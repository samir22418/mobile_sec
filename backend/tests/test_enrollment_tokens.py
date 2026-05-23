from __future__ import annotations

from tests.conftest import sample_payload


def test_analyst_can_create_enrollment_token_and_use_it_for_telemetry(client):
    create_response = client.post(
        "/api/v1/enrollment-tokens",
        json={"label": "Lab phone", "device_id": "android-lab-001"},
    )

    assert create_response.status_code == 201
    body = create_response.json()
    assert body["token"].startswith("aegis_enroll_")
    assert body["device_id"] == "android-lab-001"

    telemetry_response = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="from-generated-token", device_id="android-lab-001"),
        headers={"Authorization": f"Bearer {body['token']}"},
    )

    assert telemetry_response.status_code == 202
    assert telemetry_response.json()["processing_status"] == "PROCESSED"


def test_revoked_enrollment_token_is_rejected(client):
    create_response = client.post("/api/v1/enrollment-tokens", json={"label": "Temporary token"})
    token_body = create_response.json()

    revoke_response = client.post(f"/api/v1/enrollment-tokens/{token_body['id']}/revoke")
    assert revoke_response.status_code == 200
    assert revoke_response.json()["is_active"] is False

    telemetry_response = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="revoked-token"),
        headers={"Authorization": f"Bearer {token_body['token']}"},
    )

    assert telemetry_response.status_code == 401


def test_list_enrollment_tokens_never_returns_raw_token(client):
    create_response = client.post("/api/v1/enrollment-tokens", json={"label": "List test"})
    raw_token = create_response.json()["token"]

    list_response = client.get("/api/v1/enrollment-tokens")

    assert list_response.status_code == 200
    assert list_response.json()["items"]
    assert raw_token not in list_response.text
    assert "token_hash" not in list_response.text
