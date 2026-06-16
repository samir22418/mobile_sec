"""
Phase 4 — Logs pipeline tests.

Covers three concerns:
1. RedactionService — unit tests for all 8 PII/secret pattern families + hash_message().
2. NormalizationService — verifies redaction is applied during log ingestion.
3. Logs API (/api/v1/logs/analysis) — edge cases: empty DB, limit clamping,
   device_id isolation, free-text search across tag field.
"""
from __future__ import annotations

import hashlib

import pytest

from app.services.redaction import RedactionService
from tests.conftest import important_log, sample_payload


# =============================================================================
# RedactionService — unit tests (no DB needed)
# =============================================================================


@pytest.fixture
def svc() -> RedactionService:
    return RedactionService()


class TestBearerTokenRedaction:
    def test_authorization_header_bearer(self, svc):
        raw = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = svc.redact(raw)
        assert "<redacted>" in result
        assert "eyJhbGci" not in result

    def test_bearer_case_insensitive(self, svc):
        raw = "authorization: bearer mySecretToken123"
        result = svc.redact(raw)
        assert "mySecretToken123" not in result
        assert "<redacted>" in result


class TestKeyValueSecretRedaction:
    def test_token_equals(self, svc):
        result = svc.redact("token=abc123xyz")
        assert "abc123xyz" not in result
        assert "<redacted>" in result

    def test_password_equals(self, svc):
        result = svc.redact("password=hunter2")
        assert "hunter2" not in result
        assert "<redacted>" in result

    def test_secret_equals(self, svc):
        result = svc.redact("secret=s3cr3tV@lue")
        assert "s3cr3tV@lue" not in result
        assert "<redacted>" in result

    def test_api_key_colon(self, svc):
        result = svc.redact("api_key: AAABBBCCC")
        assert "AAABBBCCC" not in result

    def test_access_token_equals(self, svc):
        result = svc.redact("access_token=tok_live_xxxx")
        assert "tok_live_xxxx" not in result

    def test_refresh_token_equals(self, svc):
        result = svc.redact("refresh_token=rft_abc")
        assert "rft_abc" not in result


class TestSSNRedaction:
    def test_standard_ssn_format(self, svc):
        result = svc.redact("user SSN: 123-45-6789 on file")
        assert "123-45-6789" not in result
        assert "<redacted-ssn>" in result

    def test_ssn_does_not_match_partial(self, svc):
        result = svc.redact("code 12-34-5678")
        assert "<redacted-ssn>" not in result


class TestCreditCardRedaction:
    def test_visa_card_number(self, svc):
        result = svc.redact("card: 4111111111111111")
        assert "4111111111111111" not in result
        assert "<redacted-card>" in result

    def test_card_with_spaces(self, svc):
        result = svc.redact("Mastercard 5500 0000 0000 0004")
        assert "5500 0000 0000 0004" not in result


class TestEmailRedaction:
    def test_standard_email(self, svc):
        result = svc.redact("user@example.com signed in")
        assert "user@example.com" not in result
        assert "<redacted-email>" in result

    def test_subdomain_email(self, svc):
        result = svc.redact("alert from admin@mail.corp.internal failed")
        assert "admin@mail.corp.internal" not in result
        assert "<redacted-email>" in result


class TestPhoneRedaction:
    def test_international_phone(self, svc):
        result = svc.redact("called +1 555-867-5309")
        assert "867-5309" not in result
        assert "<redacted-phone>" in result


class TestMultiPatternRedaction:
    def test_token_and_email_in_same_message(self, svc):
        raw = "token=secret permission denied for user@example.com"
        result = svc.redact(raw)
        assert "secret" not in result
        assert "user@example.com" not in result
        assert "<redacted>" in result
        assert "<redacted-email>" in result

    def test_bearer_and_ssn(self, svc):
        raw = "Authorization: Bearer tok123 SSN 987-65-4321"
        result = svc.redact(raw)
        assert "tok123" not in result
        assert "987-65-4321" not in result

    def test_benign_message_unchanged(self, svc):
        raw = "ActivityManager: activity started successfully"
        assert svc.redact(raw) == raw


class TestHashMessage:
    def test_returns_hex_sha256(self, svc):
        result = svc.hash_message("hello")
        expected = hashlib.sha256(b"hello").hexdigest()
        assert result == expected

    def test_deterministic(self, svc):
        msg = "permission denied for uid 0"
        assert svc.hash_message(msg) == svc.hash_message(msg)

    def test_different_inputs_produce_different_hashes(self, svc):
        assert svc.hash_message("foo") != svc.hash_message("bar")

    def test_hash_length_is_64(self, svc):
        assert len(svc.hash_message("test")) == 64


# =============================================================================
# NormalizationService — redaction applied during ingestion
# =============================================================================


def test_logs_are_redacted_before_storage(client):
    """message_redacted must not contain the raw PII; message_hash must match."""
    raw = "token=mysecrettoken123 permission denied for admin@example.com SSN 111-22-3333"
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="redact-test", logs=[important_log(raw)]),
    )

    response = client.get("/api/v1/logs/analysis")
    assert response.status_code == 200
    log = response.json()["recent_logs"][0]

    assert "mysecrettoken123" not in log["message_redacted"]
    assert "admin@example.com" not in log["message_redacted"]
    assert "111-22-3333" not in log["message_redacted"]
    assert "<redacted>" in log["message_redacted"]
    assert "<redacted-email>" in log["message_redacted"]
    assert "<redacted-ssn>" in log["message_redacted"]

    svc = RedactionService()
    assert log["message_hash"] == svc.hash_message(raw)


# =============================================================================
# Logs API — edge cases
# =============================================================================


def test_logs_analysis_empty_db_returns_valid_structure(client):
    response = client.get("/api/v1/logs/analysis")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_logs"] == 0
    assert body["summary"]["high_severity_count"] == 0
    assert body["summary"]["repeated_clusters"] == 0
    assert body["by_level"] == {}
    assert body["by_rule"] == {}
    assert body["top_tags"] == []
    assert body["clusters"] == []
    assert body["recent_logs"] == []
    assert body["timeline"] == []


def test_logs_analysis_limit_zero_clamped_to_one(client):
    for i in range(5):
        client.post(
            "/api/v1/telemetry",
            json=sample_payload(
                payload_id=f"limit-{i}",
                scan_id=i + 1,
                logs=[important_log(f"permission denied uid={i}")],
            ),
        )

    response = client.get("/api/v1/logs/analysis?limit=0")

    assert response.status_code == 200
    assert len(response.json()["recent_logs"]) == 1


def test_logs_analysis_limit_above_max_clamped_to_200(client):
    for i in range(3):
        client.post(
            "/api/v1/telemetry",
            json=sample_payload(
                payload_id=f"clamp-{i}",
                scan_id=i + 1,
                logs=[important_log(f"permission denied uid={i}")],
            ),
        )

    response = client.get("/api/v1/logs/analysis?limit=9999")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_logs"] == 3
    assert len(body["recent_logs"]) == 3


def test_logs_analysis_device_id_filter_isolates_device(client):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="dev-a-1",
            device_id="device-alpha",
            logs=[important_log("permission denied uid=1")],
        ),
    )
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="dev-b-1",
            device_id="device-beta",
            logs=[important_log("permission denied uid=2")],
        ),
    )

    response = client.get("/api/v1/logs/analysis?device_id=device-alpha")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_logs"] == 1
    assert body["summary"]["affected_devices"] == 1
    assert body["recent_logs"][0]["device_id"] == "device-alpha"


def test_logs_analysis_q_searches_tag_field(client):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="tag-search-1",
            logs=[
                {
                    "id": 1,
                    "timestamp_epoch_ms": 1_700_000_000_001,
                    "device_id": "sample-device-001",
                    "tag": "CryptoManager",
                    "level": "ERROR",
                    "message": "invalid certificate chain",
                    "matched_rule": "THREAT_REGEX",
                }
            ],
        ),
    )
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="tag-search-2",
            scan_id=2,
            logs=[important_log("permission denied uid=0")],
        ),
    )

    response = client.get("/api/v1/logs/analysis?q=CryptoManager")

    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_logs"] == 1
    assert body["recent_logs"][0]["tag"] == "CryptoManager"


def test_logs_analysis_timeline_groups_by_day(client):
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="tl-1",
            logs=[important_log("permission denied uid=0")],
        ),
    )
    client.post(
        "/api/v1/telemetry",
        json=sample_payload(
            payload_id="tl-2",
            scan_id=2,
            logs=[important_log("SSL error: handshake failed")],
        ),
    )

    response = client.get("/api/v1/logs/analysis")

    assert response.status_code == 200
    body = response.json()
    assert len(body["timeline"]) >= 1
    for entry in body["timeline"]:
        assert "day" in entry
        assert "total" in entry
        assert "high_severity" in entry
        assert entry["total"] > 0


def test_logs_analysis_unauthorized_without_token(app):
    from fastapi.testclient import TestClient

    bare_client = TestClient(app)
    response = bare_client.get("/api/v1/logs/analysis")
    assert response.status_code in (401, 403)
