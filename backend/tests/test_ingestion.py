from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import BACKEND_DIR, Settings
from app.main import create_app
from app.models import TelemetryPayload
from tests.conftest import sample_payload


def test_valid_payload_returns_202(client):
    response = client.post("/api/v1/telemetry", json=sample_payload())

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["duplicate"] is False
    assert body["processing_status"] == "PROCESSED"


def test_duplicate_payload_is_idempotent(client, app):
    payload = sample_payload()

    first = client.post("/api/v1/telemetry", json=payload)
    second = client.post("/api/v1/telemetry", json=payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["duplicate"] is True

    session = app.state.session_factory()
    try:
        rows = session.scalars(select(TelemetryPayload)).all()
        assert len(rows) == 1
    finally:
        session.close()


def test_missing_required_field_returns_400(client):
    payload = sample_payload()
    payload.pop("device_report")

    response = client.post("/api/v1/telemetry", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "invalid_schema"


def test_invalid_enrollment_token_returns_401(client):
    response = client.post(
        "/api/v1/telemetry",
        json=sample_payload(),
        headers={"Authorization": "Bearer wrong-token"},
    )

    assert response.status_code == 401


def test_telemetry_rate_limit_returns_429(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'rate-limit.db').as_posix()}",
        raw_payload_dir=tmp_path / "raw",
        telemetry_schema_path=BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json",
        accepted_enrollment_tokens=("sample-token",),
        analyst_tokens=("sample-token",),
        process_inline=True,
        telemetry_rate_limit_max_requests=1,
        telemetry_rate_limit_window_seconds=60,
    )
    client = TestClient(create_app(settings))
    client.headers.update({"Authorization": "Bearer sample-token"})

    payload = sample_payload(payload_id="first")
    assert client.post("/api/v1/telemetry", json=payload).status_code == 202

    duplicate = client.post("/api/v1/telemetry", json=payload)
    assert duplicate.status_code == 202
    assert duplicate.json()["duplicate"] is True

    response = client.post("/api/v1/telemetry", json=sample_payload(payload_id="second"))

    assert response.status_code == 429
    assert response.json()["detail"]["error"] == "rate_limited"

