from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import TelemetryPayload
from app.ai.analyzer import AIAnalysisService
from app.services.normalization import NormalizationService
from app.services.raw_store import RawPayloadStore
from app.risk.scorer import RiskScoringService


class TelemetryWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        raw_store: RawPayloadStore,
        normalizer: NormalizationService | None = None,
        risk_scorer: RiskScoringService | None = None,
        ai_service: AIAnalysisService | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.raw_store = raw_store
        self.normalizer = normalizer or NormalizationService()
        self.risk_scorer = risk_scorer or RiskScoringService()
        self.ai_service = ai_service or AIAnalysisService()

    def process_one(self, payload_id: str) -> None:
        session = self.session_factory()
        try:
            record = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
            if record is None:
                raise ValueError(f"payload not found: {payload_id}")
            if record.processing_status == "PROCESSED":
                return

            record.processing_status = "PROCESSING"
            record.processing_error = None
            session.commit()

            payload = self.raw_store.load(record.raw_payload_path)
            self.normalizer.normalize(session, payload)
            session.flush()
            assessment = self.risk_scorer.score(session, record.payload_id, record.device_id)
            session.flush()
            self.ai_service.maybe_analyze(session, record.payload_id, record.device_id, assessment)
            record.processing_status = "PROCESSED"
            session.commit()
        except Exception as error:
            session.rollback()
            failed = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
            if failed is not None:
                failed.processing_status = "FAILED"
                failed.processing_error = str(error)
                session.commit()
            raise
        finally:
            session.close()

    def process_pending(self, limit: int = 25) -> int:
        session = self.session_factory()
        try:
            records = session.scalars(
                select(TelemetryPayload)
                .where(TelemetryPayload.processing_status.in_(["ACCEPTED"]))
                .order_by(TelemetryPayload.received_at.asc())
                .limit(limit)
            ).all()
        finally:
            session.close()

        for record in records:
            self.process_one(record.payload_id)
        return len(records)
