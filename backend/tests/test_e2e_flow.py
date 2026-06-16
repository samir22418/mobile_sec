"""End-to-end test of the AEGIS backend pipeline.

Exercises the full lifecycle a real deployment goes through:

1. An analyst issues a device-specific enrollment token via the admin API.
2. The device uses that token to submit a telemetry payload (rooted device,
   a sideloaded app requesting sensitive permissions, and a threat-matching
   log line).
3. The backend validates, stores, and (inline) processes the payload, then
   computes a risk assessment.
4. An analyst queries /devices, /devices/{id}/latest-risk,
   /devices/{id}/timeline, and /logs/analysis and confirms the data is
   consistent end-to-end.
5. An analyst leaves feedback on the resulting finding.
6. The enrollment token is revoked and a follow-up submission with the same
   (now-revoked) token is rejected.
7. A duplicate of the original payload is replayed and confirmed idempotent.

This intentionally avoids any real DB/Kafka/Play-Integrity dependencies —
it runs entirely against the FastAPI app with `process_inline=True` and a
throwaway SQLite database (see conftest.py), so it can run anywhere `pytest`
runs without external services.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import BACKEND_DIR, Settings
from app.main import create_app
from tests.conftest import important_log, sample_payload, suspicious_app


def _make_client(tmp_path, **settings_overrides):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'e2e.db').as_posix()}",
        raw_payload_dir=tmp_path / "raw",
        telemetry_schema_path=BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json",
        accepted_enrollment_tokens=("seed-token",),
        analyst_tokens=("analyst-token",),
        process_inline=True,
        **settings_overrides,
    )
    return TestClient(create_app(settings))


def test_full_pipeline_enroll_ingest_score_review(tmp_path):
    client = _make_client(tmp_path)
    device_id = "e2e-device-001"

    # --- Step 1: analyst mints a device-scoped enrollment token -----------
    analyst_headers = {"Authorization": "Bearer analyst-token"}

    create_resp = client.post(
        "/api/v1/enrollment-tokens",
        json={"label": "E2E lab phone", "device_id": device_id, "expires_at": None},
        headers=analyst_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    token_record = create_resp.json()
    enrollment_token = token_record["token"]
    token_id = token_record["id"]
    assert token_record["is_active"] is True
    assert token_record["device_id"] == device_id

    # Token list shows metadata but never the raw token again
    list_resp = client.get("/api/v1/enrollment-tokens", headers=analyst_headers)
    assert list_resp.status_code == 200
    listed = next(item for item in list_resp.json()["items"] if item["id"] == token_id)
    assert "token" not in listed

    # --- Step 2: device submits telemetry using the freshly minted token --
    device_headers = {"Authorization": f"Bearer {enrollment_token}"}

    payload = sample_payload(
        payload_id="e2e-payload-1",
        scan_id=1,
        device_id=device_id,
        rooted=True,
        integrity="FAILS",
        bootloader="orange",
        apps=[suspicious_app("com.example.spyware")],
        logs=[important_log("permission denied: token=abcd1234 for user@example.com")],
    )

    ingest_resp = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert ingest_resp.status_code == 202, ingest_resp.text
    ingest_body = ingest_resp.json()
    assert ingest_body["accepted"] is True
    assert ingest_body["duplicate"] is False
    assert ingest_body["processing_status"] == "PROCESSED"

    # A wrong/unenrolled token must not be able to submit on behalf of this device
    bad_resp = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="e2e-payload-bad", device_id=device_id),
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert bad_resp.status_code == 401

    # --- Step 3: replaying the same payload is idempotent -----------------
    replay_resp = client.post("/api/v1/telemetry", json=payload, headers=device_headers)
    assert replay_resp.status_code == 202
    assert replay_resp.json()["duplicate"] is True

    # --- Step 4a: analyst sees the device with an elevated risk score -----
    devices_resp = client.get("/api/v1/devices", headers=analyst_headers)
    assert devices_resp.status_code == 200
    device_entry = next(item for item in devices_resp.json()["items"] if item["device_id"] == device_id)
    assert device_entry["payload_count"] == 1
    # Rooted + FAILS integrity + orange bootloader + sideloaded sensitive-perm app
    # should push this well above "Low".
    assert device_entry["latest_risk_label"] in {"High", "Critical"}
    assert device_entry["latest_risk_score"] >= 50

    # --- Step 4b: latest-risk endpoint agrees and explains why -------------
    risk_resp = client.get(f"/api/v1/devices/{device_id}/latest-risk", headers=analyst_headers)
    assert risk_resp.status_code == 200
    risk = risk_resp.json()
    assert risk["device_id"] == device_id
    assert risk["needs_human_review"] is True
    reasons_text = " ".join(risk["reasons"])
    assert "Root" in reasons_text
    assert "Play Integrity" in reasons_text

    # --- Step 4c: timeline shows the payload with its embedded risk -------
    timeline_resp = client.get(f"/api/v1/devices/{device_id}/timeline", headers=analyst_headers)
    assert timeline_resp.status_code == 200
    timeline_items = timeline_resp.json()["items"]
    assert len(timeline_items) == 1
    assert timeline_items[0]["payload_id"] == "e2e-payload-1"
    assert timeline_items[0]["risk"]["risk_label"] == risk["risk_label"]

    # --- Step 4d: logs analysis surfaces the redacted threat log ----------
    logs_resp = client.get(
        "/api/v1/logs/analysis",
        params={"device_id": device_id},
        headers=analyst_headers,
    )
    assert logs_resp.status_code == 200
    logs_body = logs_resp.json()
    assert logs_body["summary"]["total_logs"] == 1
    assert logs_body["summary"]["threat_regex_count"] == 1
    recent = logs_body["recent_logs"][0]
    # Secrets and PII must be redacted before they ever reach this response.
    assert "abcd1234" not in recent["message_redacted"]
    assert "user@example.com" not in recent["message_redacted"]
    assert "<redacted>" in recent["message_redacted"] or "<redacted-email>" in recent["message_redacted"]

    # --- Step 5: analyst records feedback on the finding -------------------
    feedback_resp = client.post(
        f"/api/v1/findings/{risk['payload_id']}/feedback",
        json={
            "payload_id": risk["payload_id"],
            "analyst_id": "analyst-1",
            "label": "TRUE_POSITIVE",
            "notes": "Confirmed rooted device with sideloaded SMS-reading app.",
        },
        headers=analyst_headers,
    )
    assert feedback_resp.status_code == 201, feedback_resp.text
    assert feedback_resp.json()["label"] == "TRUE_POSITIVE"

    # Invalid label is rejected with 400
    bad_feedback = client.post(
        f"/api/v1/findings/{risk['payload_id']}/feedback",
        json={
            "payload_id": risk["payload_id"],
            "analyst_id": "analyst-1",
            "label": "NOT_A_REAL_LABEL",
        },
        headers=analyst_headers,
    )
    assert bad_feedback.status_code == 400

    # --- Step 6: revoke the enrollment token --------------------------------
    revoke_resp = client.post(f"/api/v1/enrollment-tokens/{token_id}/revoke", headers=analyst_headers)
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["is_active"] is False

    # A revoked token can no longer submit new telemetry
    post_revoke_resp = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="e2e-payload-2", scan_id=2, device_id=device_id),
        headers=device_headers,
    )
    assert post_revoke_resp.status_code == 401, post_revoke_resp.text


def test_unauthenticated_requests_are_rejected(tmp_path):
    client = _make_client(tmp_path)

    # No Authorization header at all -> 401/403 from HTTPBearer, never a 200
    assert client.get("/api/v1/devices").status_code in (401, 403)
    assert client.post("/api/v1/telemetry", json=sample_payload()).status_code in (401, 403)

    # Analyst token cannot be used to submit telemetry, and vice versa
    assert client.get(
        "/api/v1/devices", headers={"Authorization": "Bearer seed-token"}
    ).status_code == 401
    assert client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="cross-token"),
        headers={"Authorization": "Bearer analyst-token"},
    ).status_code == 401
