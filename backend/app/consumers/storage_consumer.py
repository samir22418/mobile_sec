from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.kafka import get_consumer
from app.models import TelemetryPayload
from app.services.normalization import NormalizationService
from app.services.raw_store import RawPayloadStore

logger = logging.getLogger(__name__)


class StorageConsumer:
    def __init__(
        self,
        settings: Settings,
        session_factory: sessionmaker[Session],
        raw_store: RawPayloadStore,
        *,
        consumer=None,
    ) -> None:
        self.settings = settings
        self.session_factory = session_factory
        self.raw_store = raw_store
        self.normalizer = NormalizationService()
        self.consumer = consumer or get_consumer(settings, settings.kafka_telemetry_topic, group_id="storage_group")
        
    def run(self):
        logger.info("StorageConsumer started")
        for message in self.consumer:
            data = message.value
            payload_id = data.get("payload_id")
            if not payload_id:
                continue
                
            session = self.session_factory()
            try:
                record = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
                if not record:
                    continue
                    
                payload = self.raw_store.load(record.raw_payload_path)
                self.normalizer.normalize(session, payload)
                session.commit()
            except Exception as e:
                logger.error(f"StorageConsumer error for {payload_id}: {e}")
                session.rollback()
            finally:
                session.close()
