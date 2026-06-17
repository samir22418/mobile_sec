from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.ai.analyzer import AIAnalysisService
from app.config import Settings
from app.models import DeviceReport, TelemetryPayload
from app.risk.scorer import RiskScoringService
from app.services.normalization import NormalizationService
from app.services.play_integrity import PlayIntegrityError, PlayIntegrityService
from app.services.raw_store import RawPayloadStore

logger = logging.getLogger(__name__)


class TelemetryWorker:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        raw_store: RawPayloadStore,
        normalizer: NormalizationService | None = None,
        risk_scorer: RiskScoringService | None = None,
        ai_service: AIAnalysisService | None = None,
        play_integrity_service: PlayIntegrityService | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.raw_store = raw_store
        self.normalizer = normalizer or NormalizationService()
        self.risk_scorer = risk_scorer or RiskScoringService()
        self.ai_service = ai_service or AIAnalysisService(settings=settings)
        self._play_integrity = play_integrity_service or PlayIntegrityService("", "")

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

            self._verify_play_integrity(session, payload_id, payload)
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

    def _verify_play_integrity(
        self, session: Session, payload_id: str, payload: dict
    ) -> None:
        device_report_data = payload.get("device_report", {})
        token = device_report_data.get("integrity_token")
        nonce = device_report_data.get("integrity_nonce") or ""

        if not token or not self._play_integrity.is_configured:
            return

        # Replay protection: reject if this nonce was used in a prior payload
        if nonce:
            prior = session.scalar(
                select(DeviceReport).where(
                    DeviceReport.integrity_nonce == nonce,
                    DeviceReport.payload_id != payload_id,
                )
            )
            if prior is not None:
                logger.warning(
                    "Play Integrity replay detected: nonce already used in payload %s — marking FAILS",
                    prior.payload_id,
                )
                dr = session.scalar(select(DeviceReport).where(DeviceReport.payload_id == payload_id))
                if dr is not None:
                    dr.verified_integrity_verdict = "FAILS"
                return

        try:
            vi = self._play_integrity.verify_token(token, nonce)
            logger.info(
                "Play Integrity verified payload_id=%s verdict=%s nonce_valid=%s",
                payload_id, vi.verdict, vi.nonce_valid,
            )
        except PlayIntegrityError as exc:
            logger.warning("Play Integrity API error for %s: %s", payload_id, exc)
            vi_verdict = "API_ERROR"
        else:
            vi_verdict = vi.verdict

        dr = session.scalar(select(DeviceReport).where(DeviceReport.payload_id == payload_id))
        if dr is not None:
            dr.verified_integrity_verdict = vi_verdict

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
