from __future__ import annotations

from sqlalchemy import select

from app.models import AIModelRun
from app.ai.analyzer import AIAnalysisService
from app.services.raw_store import RawPayloadStore
from app.services.worker import TelemetryWorker
from tests.conftest import sample_payload, suspicious_app


class InvalidJsonAnalyzer:
    model_name = "bad-json"
    prompt_version = "test"

    def analyze(self, evidence_bundle: dict) -> str:
        return "not-json"


class MissingEvidenceAnalyzer:
    model_name = "missing-evidence"
    prompt_version = "test"

    def analyze(self, evidence_bundle: dict) -> str:
        return '{"findings":[{"title":"unsupported"}]}'


def test_low_risk_payload_skips_llm_stub(client, app):
    response = client.post("/api/v1/telemetry", json=sample_payload())
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        assert session.scalar(select(AIModelRun)) is None
    finally:
        session.close()


def test_high_risk_payload_creates_ai_model_run(client, app):
    response = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="ai-high", rooted=True, apps=[suspicious_app()]),
    )
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        run = session.scalar(select(AIModelRun).where(AIModelRun.payload_id == "ai-high"))
        assert run is not None
        assert run.status == "SUCCEEDED"
        assert run.model_role == "primary_llm_analyst"
    finally:
        session.close()


def test_invalid_ai_json_is_stored_as_failed_run(app):
    payload_id = "bad-ai-json"
    app.state.raw_store.store(
        payload_id,
        sample_payload(payload_id=payload_id, rooted=True, apps=[suspicious_app()]),
    )
    session = app.state.session_factory()
    try:
        from app.models import TelemetryPayload

        session.add(
            TelemetryPayload(
                payload_id=payload_id,
                device_id="sample-device-001",
                scan_id=1,
                payload_created_at_epoch_ms=1,
                raw_payload_path=str(app.state.raw_store.root / f"{payload_id}.json"),
                processing_status="ACCEPTED",
            )
        )
        session.commit()
    finally:
        session.close()

    worker = TelemetryWorker(
        app.state.session_factory,
        RawPayloadStore(app.state.raw_store.root),
        ai_service=AIAnalysisService(InvalidJsonAnalyzer()),
    )
    worker.process_one(payload_id)

    session = app.state.session_factory()
    try:
        run = session.scalar(select(AIModelRun).where(AIModelRun.payload_id == payload_id))
        assert run.status == "FAILED"
    finally:
        session.close()


def test_ai_finding_without_evidence_refs_is_rejected(app):
    payload_id = "bad-ai-evidence"
    app.state.raw_store.store(
        payload_id,
        sample_payload(payload_id=payload_id, rooted=True, apps=[suspicious_app()]),
    )
    session = app.state.session_factory()
    try:
        from app.models import TelemetryPayload

        session.add(
            TelemetryPayload(
                payload_id=payload_id,
                device_id="sample-device-001",
                scan_id=1,
                payload_created_at_epoch_ms=1,
                raw_payload_path=str(app.state.raw_store.root / f"{payload_id}.json"),
                processing_status="ACCEPTED",
            )
        )
        session.commit()
    finally:
        session.close()

    worker = TelemetryWorker(
        app.state.session_factory,
        RawPayloadStore(app.state.raw_store.root),
        ai_service=AIAnalysisService(MissingEvidenceAnalyzer()),
    )
    worker.process_one(payload_id)

    session = app.state.session_factory()
    try:
        run = session.scalar(select(AIModelRun).where(AIModelRun.payload_id == payload_id))
        assert run.status == "FAILED"
    finally:
        session.close()

