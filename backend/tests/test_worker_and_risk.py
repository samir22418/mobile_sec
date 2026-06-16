from __future__ import annotations

from sqlalchemy import select

from app.models import (
    AppInventoryCurrent,
    ImportantLog,
    RiskAssessment,
    TelemetryPayload,
)
from app.services.raw_store import RawPayloadStore
from app.services.worker import TelemetryWorker
from tests.conftest import important_log, sample_payload, suspicious_app


def test_worker_normalizes_device_apps_and_redacted_logs(client, app):
    payload = sample_payload(
        apps=[suspicious_app()],
        logs=[important_log("token=secret api_key=abc123 user@example.com 4111111111111111 123-45-6789")],
    )

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        app_row = session.scalar(select(AppInventoryCurrent).where(AppInventoryCurrent.package_name == "com.example.suspicious"))
        log_row = session.scalar(select(ImportantLog))
        assert app_row is not None
        assert app_row.install_source == "SIDELOADED"
        assert log_row is not None
        assert "secret" not in log_row.message_redacted
        assert "abc123" not in log_row.message_redacted
        assert "user@example.com" not in log_row.message_redacted
        assert "4111111111111111" not in log_row.message_redacted
        assert "123-45-6789" not in log_row.message_redacted
        assert len(log_row.message_hash) == 64
    finally:
        session.close()


def test_full_app_snapshot_replaces_stale_current_inventory(client, app):
    first = sample_payload(payload_id="first", apps=[suspicious_app("com.example.old")])
    second = sample_payload(payload_id="second", scan_id=2, apps=[])

    assert client.post("/api/v1/telemetry", json=first).status_code == 202
    assert client.post("/api/v1/telemetry", json=second).status_code == 202

    session = app.state.session_factory()
    try:
        apps = session.scalars(select(AppInventoryCurrent)).all()
        assert apps == []
    finally:
        session.close()


def test_failed_processing_marks_payload_failed(app, tmp_path):
    session = app.state.session_factory()
    try:
        record = TelemetryPayload(
            payload_id="bad-payload",
            device_id="sample-device-001",
            scan_id=9,
            payload_created_at_epoch_ms=1,
            raw_payload_path=str(tmp_path / "missing.json"),
            processing_status="ACCEPTED",
        )
        session.add(record)
        session.commit()
    finally:
        session.close()

    worker = TelemetryWorker(app.state.session_factory, RawPayloadStore(tmp_path / "raw"))
    try:
        worker.process_one("bad-payload")
    except FileNotFoundError:
        pass

    session = app.state.session_factory()
    try:
        record = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == "bad-payload"))
        assert record.processing_status == "FAILED"
        assert record.processing_error
    finally:
        session.close()


def test_rooted_failed_integrity_sideloaded_app_increases_risk(client, app):
    payload = sample_payload(
        payload_id="high-risk",
        rooted=True,
        integrity="FAILS",
        patch_date="2020-01-01",
        bootloader="orange",
        apps=[suspicious_app()],
        logs=[important_log()],
    )

    response = client.post("/api/v1/telemetry", json=payload)
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == "high-risk"))
        assert assessment is not None
        assert assessment.risk_score >= 75
        assert assessment.risk_label == "Critical"
        assert assessment.needs_human_review is True
    finally:
        session.close()


def test_empty_logs_are_accepted(client, app):
    response = client.post("/api/v1/telemetry", json=sample_payload(logs=[]))
    assert response.status_code == 202

    session = app.state.session_factory()
    try:
        assert session.scalar(select(ImportantLog)) is None
        assessment = session.scalar(select(RiskAssessment))
        assert assessment is not None
    finally:
        session.close()

