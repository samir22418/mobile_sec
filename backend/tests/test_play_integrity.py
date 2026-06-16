"""Tests for PlayIntegrityService and its integration with the scoring pipeline."""

from __future__ import annotations

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import BACKEND_DIR, Settings
from app.main import create_app
from app.models import DeviceReport, TelemetryPayload
from app.risk.scorer import RiskScoringService
from app.services.play_integrity import (
    PlayIntegrityError,
    PlayIntegrityService,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STRONG_RESPONSE = {
    "tokenPayloadExternal": {
        "requestDetails": {"nonce": "nonce-abc", "requestPackageName": "com.example.aegis"},
        "deviceIntegrity": {
            "deviceRecognitionVerdict": ["MEETS_STRONG_INTEGRITY", "MEETS_DEVICE_INTEGRITY"]
        },
        "appIntegrity": {"appRecognitionVerdict": "PLAY_RECOGNIZED"},
        "accountDetails": {"appLicensingVerdict": "LICENSED"},
    }
}

_DEVICE_RESPONSE = {
    "tokenPayloadExternal": {
        "requestDetails": {"nonce": "nonce-abc"},
        "deviceIntegrity": {"deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]},
        "appIntegrity": {},
        "accountDetails": {},
    }
}


def _mock_urlopen(response_dict: dict):
    mock_resp = MagicMock()
    mock_resp.__enter__ = MagicMock(return_value=mock_resp)
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.read = MagicMock(return_value=json.dumps(response_dict).encode())
    return mock_resp


# ---------------------------------------------------------------------------
# Test 1: Unconfigured service returns bypass verdict
# ---------------------------------------------------------------------------

def test_service_not_configured_returns_bypass():
    svc = PlayIntegrityService("", "")
    result = svc.verify_token("any-encrypted-token", "any-nonce")
    assert result.verdict == "REQUIRES_BACKEND_VERIFICATION"
    assert result.nonce_valid is True
    assert svc.is_configured is False


# ---------------------------------------------------------------------------
# Test 2: Configured service resolves MEETS_STRONG_INTEGRITY
# ---------------------------------------------------------------------------

def test_service_verifies_strong_integrity():
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(_STRONG_RESPONSE)):
        svc = PlayIntegrityService("fake-api-key", "com.example.aegis")
        result = svc.verify_token("encrypted-token", "nonce-abc")

    assert result.verdict == "MEETS_STRONG_INTEGRITY"
    assert result.nonce_valid is True
    assert result.app_recognition == "PLAY_RECOGNIZED"
    assert result.licensing_verdict == "LICENSED"


# ---------------------------------------------------------------------------
# Test 3: Nonce mismatch → FAILS (replay / tampered token)
# ---------------------------------------------------------------------------

def test_service_nonce_mismatch_returns_fails():
    tampered_response = {
        "tokenPayloadExternal": {
            "requestDetails": {"nonce": "original-nonce"},
            "deviceIntegrity": {"deviceRecognitionVerdict": ["MEETS_STRONG_INTEGRITY"]},
        }
    }
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(tampered_response)):
        svc = PlayIntegrityService("fake-api-key", "com.example.aegis")
        # expected_nonce differs from the one bound into the token
        result = svc.verify_token("encrypted-token", "attacker-nonce")

    assert result.verdict == "FAILS"
    assert result.nonce_valid is False


# ---------------------------------------------------------------------------
# Test 4: HTTP 401 from Google → PlayIntegrityError
# ---------------------------------------------------------------------------

def test_service_http_error_raises_play_integrity_error():
    http_err = urllib.error.HTTPError(
        url="https://playintegrity.googleapis.com/...",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=io.BytesIO(b"Invalid API key"),
    )
    with patch("urllib.request.urlopen", side_effect=http_err):
        svc = PlayIntegrityService("bad-key", "com.example.aegis")
        with pytest.raises(PlayIntegrityError, match="401"):
            svc.verify_token("some-token", "some-nonce")


# ---------------------------------------------------------------------------
# Test 5: Empty deviceRecognitionVerdict → FAILS
# ---------------------------------------------------------------------------

def test_service_empty_device_verdicts_returns_fails():
    empty_response = {
        "tokenPayloadExternal": {
            "requestDetails": {"nonce": "n1"},
            "deviceIntegrity": {"deviceRecognitionVerdict": []},
        }
    }
    with patch("urllib.request.urlopen", return_value=_mock_urlopen(empty_response)):
        svc = PlayIntegrityService("key", "pkg")
        result = svc.verify_token("token", "n1")

    assert result.verdict == "FAILS"
    assert result.nonce_valid is True


# ---------------------------------------------------------------------------
# Test 6: Risk score lowers when REQUIRES_BACKEND_VERIFICATION → verified clean
# ---------------------------------------------------------------------------

def test_risk_score_lowers_with_backend_verified_device_integrity(app):
    session = app.state.session_factory()
    try:
        tp = TelemetryPayload(
            payload_id="pi-score-low-001",
            device_id="pi-dev-001",
            scan_id=901,
            payload_created_at_epoch_ms=1_700_000_000_000,
            raw_payload_path="/dev/null",
            processing_status="PROCESSING",
        )
        session.add(tp)
        session.flush()
        dr = DeviceReport(
            payload_id="pi-score-low-001",
            device_id="pi-dev-001",
            observed_at_epoch_ms=1_700_000_000_000,
            is_rooted=False,
            root_signal_count=0,
            su_binary_found=False,
            test_keys_found=False,
            superuser_apk_found=False,
            integrity_verdict="REQUIRES_BACKEND_VERIFICATION",
            verified_integrity_verdict="MEETS_DEVICE_INTEGRITY",
            integrity_nonce="pi-nonce-low-001",
            security_patch_date="2099-01-01",
            security_patch_age_days=0,
            bootloader_state="green",
        )
        session.add(dr)
        session.commit()
    finally:
        session.close()

    session2 = app.state.session_factory()
    try:
        assessment = RiskScoringService().score(session2, "pi-score-low-001", "pi-dev-001")
        session2.commit()
        score = assessment.risk_score
        reasons = json.loads(assessment.reasons_json)
    finally:
        session2.close()

    # MEETS_DEVICE_INTEGRITY verified → score = 10 (base) + 0 = 10
    assert score == 10
    assert any("backend-verified" in r for r in reasons)


# ---------------------------------------------------------------------------
# Test 7: Risk score is maximum when backend verifies FAILS
# ---------------------------------------------------------------------------

def test_risk_score_worsens_with_backend_verified_fails(app):
    session = app.state.session_factory()
    try:
        tp = TelemetryPayload(
            payload_id="pi-score-high-001",
            device_id="pi-dev-002",
            scan_id=902,
            payload_created_at_epoch_ms=1_700_000_000_000,
            raw_payload_path="/dev/null",
            processing_status="PROCESSING",
        )
        session.add(tp)
        session.flush()
        dr = DeviceReport(
            payload_id="pi-score-high-001",
            device_id="pi-dev-002",
            observed_at_epoch_ms=1_700_000_000_000,
            is_rooted=False,
            root_signal_count=0,
            su_binary_found=False,
            test_keys_found=False,
            superuser_apk_found=False,
            integrity_verdict="REQUIRES_BACKEND_VERIFICATION",
            verified_integrity_verdict="FAILS",
            integrity_nonce="pi-nonce-high-001",
            security_patch_date="2099-01-01",
            security_patch_age_days=0,
            bootloader_state="green",
        )
        session.add(dr)
        session.commit()
    finally:
        session.close()

    session2 = app.state.session_factory()
    try:
        assessment = RiskScoringService().score(session2, "pi-score-high-001", "pi-dev-002")
        session2.commit()
        score_fails = assessment.risk_score
    finally:
        session2.close()

    # FAILS verified → 10 + 35 = 45 vs REQUIRES_BACKEND_VERIFICATION → 10 + 18 = 28
    assert score_fails == 45


# ---------------------------------------------------------------------------
# Test 8: Worker end-to-end — mocked Google API response stored in DB
# ---------------------------------------------------------------------------

def test_worker_stores_verified_verdict_via_mocked_google_api(tmp_path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'pi-e2e.db').as_posix()}",
        raw_payload_dir=tmp_path / "raw",
        telemetry_schema_path=BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json",
        accepted_enrollment_tokens=("tok",),
        analyst_tokens=("tok",),
        process_inline=True,
        google_play_integrity_api_key="fake-api-key-e2e",
        google_play_integrity_package_name="com.example.aegis",
    )
    app_inst = create_app(settings)
    http_client = TestClient(app_inst)
    http_client.headers.update({"Authorization": "Bearer tok"})

    payload = {
        "payload_id": "pi-e2e-001",
        "scan_id": 1,
        "device_id": "pi-e2e-device",
        "created_at_epoch_ms": 1_700_000_000_001,
        "device_report": {
            "device_id": "pi-e2e-device",
            "timestamp_epoch_ms": 1_700_000_000_001,
            "root_detection": {
                "su_binary_found": False,
                "test_keys_found": False,
                "superuser_apk_found": False,
                "is_rooted": False,
            },
            "integrity_verdict": "REQUIRES_BACKEND_VERIFICATION",
            "integrity_details": None,
            "integrity_error_code": None,
            "integrity_token_hash_sha256": "abc123",
            "integrity_token": "fake-encrypted-token-e2e",
            "integrity_nonce": "pi-nonce-e2e-001",
            "security_patch_date": "2099-01-01",
            "bootloader_state": "green",
        },
        "app_snapshot": {
            "device_id": "pi-e2e-device",
            "timestamp_epoch_ms": 1_700_000_000_001,
            "total_app_count": 0,
            "is_delta": False,
            "apps": [],
        },
        "important_logs": [],
    }

    google_resp = {
        "tokenPayloadExternal": {
            "requestDetails": {"nonce": "pi-nonce-e2e-001"},
            "deviceIntegrity": {"deviceRecognitionVerdict": ["MEETS_STRONG_INTEGRITY"]},
            "appIntegrity": {"appRecognitionVerdict": "PLAY_RECOGNIZED"},
            "accountDetails": {"appLicensingVerdict": "LICENSED"},
        }
    }

    with patch("urllib.request.urlopen", return_value=_mock_urlopen(google_resp)):
        resp = http_client.post("/api/v1/telemetry", json=payload)

    assert resp.status_code == 202

    session = app_inst.state.session_factory()
    try:
        dr = session.scalar(
            select(DeviceReport).where(DeviceReport.payload_id == "pi-e2e-001")
        )
        assert dr is not None
        assert dr.verified_integrity_verdict == "MEETS_STRONG_INTEGRITY"
        assert dr.integrity_nonce == "pi-nonce-e2e-001"
    finally:
        session.close()
