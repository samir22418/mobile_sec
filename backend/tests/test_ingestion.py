from __future__ import annotations

from sqlalchemy import select

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

