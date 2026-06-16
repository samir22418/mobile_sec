from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.services.play_integrity import PlayIntegrityService
from app.kafka import (
    HEADER_LAST_ERROR,
    HEADER_RETRY_COUNT,
    MAX_RETRIES,
    get_consumer,
    get_producer,
    publish_to_dlq,
)
from app.models import TelemetryPayload
from app.services.raw_store import RawPayloadStore
from app.services.worker import TelemetryWorker

logger = logging.getLogger(__name__)


class TelemetryConsumer:
    """
    Single Kafka consumer for the telemetry pipeline.

    Reads from `telemetry_events`, delegates processing to TelemetryWorker
    (normalize → risk score → AI analysis), and handles retries + DLQ:

    - On success         → manual offset commit
    - On transient error → re-publish with retry_count+1 header, commit offset
    - After MAX_RETRIES  → publish to telemetry_events.dlq, mark FAILED_DLQ, commit
    """

    GROUP_ID = "aegis_processor"

    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        raw_store: RawPayloadStore,
        *,
        consumer: Any = None,
        producer: Any = None,
    ) -> None:
        self._settings = settings
        play_integrity = PlayIntegrityService(
            settings.google_play_integrity_api_key,
            settings.google_play_integrity_package_name,
        )
        self._worker = TelemetryWorker(
            session_factory, raw_store, play_integrity_service=play_integrity
        )
        self._session_factory = session_factory
        self._injected_consumer = consumer
        self._injected_producer = producer
        self._stop = False

    # ── public interface ──────────────────────────────────────────────────────

    def run(self) -> None:
        consumer = self._injected_consumer or get_consumer(
            self._settings, self._settings.kafka_telemetry_topic, self.GROUP_ID
        )
        producer = self._injected_producer or get_producer(self._settings)
        logger.info("TelemetryConsumer started — topic=%s group=%s", self._settings.kafka_telemetry_topic, self.GROUP_ID)
        try:
            for message in consumer:
                if self._stop:
                    break
                self._process_message(consumer, producer, message)
        finally:
            consumer.close()
            logger.info("TelemetryConsumer stopped")

    def stop(self) -> None:
        self._stop = True

    # ── internals ─────────────────────────────────────────────────────────────

    def _process_message(self, consumer: Any, producer: Any, message: Any) -> None:
        data = message.value or {}
        payload_id = data.get("payload_id")

        if not payload_id:
            logger.warning("Received message without payload_id — skipping")
            consumer.commit()
            return

        headers = {k: v for k, v in (message.headers or [])}
        retry_count = int(headers.get(HEADER_RETRY_COUNT, b"0").decode())

        if self._is_already_processed(payload_id):
            logger.debug("payload_id=%s already PROCESSED — skipping", payload_id)
            consumer.commit()
            return

        try:
            self._worker.process_one(payload_id)
            logger.info("Processed payload_id=%s (retry=%d)", payload_id, retry_count)
            consumer.commit()

        except Exception as exc:
            error_msg = str(exc)[:400]
            logger.warning("Failed payload_id=%s retry=%d error=%s", payload_id, retry_count, error_msg)

            if retry_count < MAX_RETRIES:
                new_headers = [
                    (HEADER_RETRY_COUNT, str(retry_count + 1).encode()),
                    (HEADER_LAST_ERROR, error_msg.encode()),
                ]
                producer.send(
                    self._settings.kafka_telemetry_topic,
                    {"payload_id": payload_id},
                    headers=new_headers,
                )
                producer.flush()
                logger.info("Re-queued payload_id=%s as retry %d/%d", payload_id, retry_count + 1, MAX_RETRIES)
            else:
                publish_to_dlq(producer, self._settings.kafka_telemetry_topic, payload_id, error_msg, retry_count)
                self._mark_failed_dlq(payload_id, error_msg)

            consumer.commit()

    def _is_already_processed(self, payload_id: str) -> bool:
        session = self._session_factory()
        try:
            record = session.scalar(
                select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id)
            )
            return record is not None and record.processing_status == "PROCESSED"
        finally:
            session.close()

    def _mark_failed_dlq(self, payload_id: str, error: str) -> None:
        session = self._session_factory()
        try:
            record = session.scalar(
                select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id)
            )
            if record is not None:
                record.processing_status = "FAILED_DLQ"
                record.processing_error = f"[DLQ] {error}"
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
