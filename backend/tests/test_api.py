from __future__ import annotations

from tests.conftest import sample_payload, suspicious_app


def test_latest_risk_returns_most_recent_assessment(client):
    client.post("/api/v1/telemetry", json=sample_payload(payload_id="first", scan_id=1))
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="second", scan_id=2, rooted=True, apps=[suspicious_app()]),
    )

    response = client.get("/api/v1/devices/sample-device-001/latest-risk")

    assert response.status_code == 200
    assert response.json()["payload_id"] == "second"


def test_timeline_orders_newest_first(client):
    client.post("/api/v1/telemetry", json=sample_payload(payload_id="first", scan_id=1))
    client.post("/api/v1/telemetry", json=sample_payload(payload_id="second", scan_id=2))

    response = client.get("/api/v1/devices/sample-device-001/timeline")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["payload_id"] for item in items] == ["second", "first"]


def test_payload_lookup_returns_processing_state(client):
    client.post("/api/v1/telemetry", json=sample_payload(payload_id="lookup"))

    response = client.get("/api/v1/payloads/lookup")

    assert response.status_code == 200
    assert response.json()["processing_status"] == "PROCESSED"
    assert response.json()["risk"] is not None


def test_feedback_endpoint_records_label(client):
    response = client.post(
        "/api/v1/findings/finding-1/feedback",
        json={
            "payload_id": "payload-1",
            "label": "TRUE_POSITIVE",
            "analyst_id": "analyst-1",
            "notes": "Confirmed during review.",
        },
    )

    assert response.status_code == 201
    assert response.json()["label"] == "TRUE_POSITIVE"


def test_feedback_rejects_invalid_label(client):
    response = client.post(
        "/api/v1/findings/finding-1/feedback",
        json={"label": "MAYBE"},
    )

    assert response.status_code == 400

