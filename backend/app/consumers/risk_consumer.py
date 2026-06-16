from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.analyzer import AIAnalysisService
from app.config import Settings
from app.kafka import get_consumer
from app.models import TelemetryPayload
from app.risk.scorer import RiskScoringService
from app.services.raw_store import RawPayloadStore

logger = logging.getLogger(__name__)


class RiskConsumer:
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
        self.risk_scorer = RiskScoringService()
        self.ai_service = AIAnalysisService()
        self.consumer = consumer or get_consumer(settings, settings.kafka_telemetry_topic, group_id="risk_group")
        
    def run(self):
        logger.info("RiskConsumer started")
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
                    
                record.processing_status = "PROCESSING"
                session.commit()
                
                assessment = self.risk_scorer.score(session, record.payload_id, record.device_id)
                session.flush()
                self.ai_service.maybe_analyze(session, record.payload_id, record.device_id, assessment)
                
                record.processing_status = "PROCESSED"
                session.commit()
            except Exception as e:
                logger.error(f"RiskConsumer error for {payload_id}: {e}")
                session.rollback()
                failed = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
                if failed:
                    failed.processing_status = "FAILED"
                    failed.processing_error = str(e)
                    session.commit()
            finally:
                session.close()
