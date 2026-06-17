from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.models import TelemetryPayload
from app.services.play_integrity import PlayIntegrityService
from app.services.raw_store import RawPayloadStore


class IngestionService:
    def __init__(
        self,
        raw_store: RawPayloadStore,
        session_factory: sessionmaker[Session],
        producer=None,
        topic: str = "telemetry_events",
        process_inline: bool = False,
        play_integrity_service: PlayIntegrityService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.raw_store = raw_store
        self.session_factory = session_factory
        self.producer = producer
        self.topic = topic
        self.process_inline = process_inline
        self._play_integrity = play_integrity_service
        self.settings = settings

    def ingest(self, session: Session, payload: dict) -> tuple[TelemetryPayload, bool]:
        payload_id = payload["payload_id"]
        
        # Try finding it first to avoid unnecessary disk I/O
        existing = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
        if existing is not None:
            return existing, True

        raw_path = self.raw_store.store(payload_id, payload)
        record = TelemetryPayload(
            payload_id=payload_id,
            device_id=payload["device_id"],
            scan_id=payload["scan_id"],
            payload_created_at_epoch_ms=payload["created_at_epoch_ms"],
            raw_payload_path=str(raw_path),
            processing_status="ACCEPTED",
        )
        session.add(record)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
            return existing, True

        session.refresh(record)

        if self.process_inline:
            from app.services.worker import TelemetryWorker
            TelemetryWorker(
                self.session_factory,
                self.raw_store,
                play_integrity_service=self._play_integrity,
                settings=self.settings,
            ).process_one(payload_id)
            session.refresh(record)
        elif self.producer:
            try:
                self.producer.send(self.topic, {"payload_id": payload_id})
                self.producer.flush()
            except Exception as exc:
                print(f"[ingestion] Kafka publish failed for {payload_id}: {exc}")

        return record, False

