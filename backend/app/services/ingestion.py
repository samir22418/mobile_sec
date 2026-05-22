from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import TelemetryPayload
from app.services.raw_store import RawPayloadStore
from app.services.worker import TelemetryWorker


class IngestionService:
    def __init__(
        self,
        raw_store: RawPayloadStore,
        session_factory: sessionmaker[Session],
        process_inline: bool,
    ) -> None:
        self.raw_store = raw_store
        self.session_factory = session_factory
        self.process_inline = process_inline

    def ingest(self, session: Session, payload: dict) -> tuple[TelemetryPayload, bool]:
        payload_id = payload["payload_id"]
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
        session.commit()
        session.refresh(record)

        if self.process_inline:
            TelemetryWorker(self.session_factory, self.raw_store).process_one(payload_id)
            session.refresh(record)

        return record, False

