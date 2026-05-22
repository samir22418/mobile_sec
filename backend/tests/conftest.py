from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import BACKEND_DIR, Settings
from app.main import create_app


@pytest.fixture
def app(tmp_path: Path):
    settings = Settings(
        database_url=f"sqlite:///{(tmp_path / 'aegis-test.db').as_posix()}",
        raw_payload_dir=tmp_path / "raw",
        telemetry_schema_path=BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json",
        accepted_enrollment_tokens=("sample-token",),
        process_inline=True,
    )
    return create_app(settings)


@pytest.fixture
def client(app):
    return TestClient(app)


def sample_payload(
    *,
    payload_id: str = "payload-1",
    scan_id: int = 1,
    device_id: str = "sample-device-001",
    enrollment_token: str = "sample-token",
    rooted: bool = False,
    integrity: str = "MEETS_DEVICE_INTEGRITY",
    patch_date: str = "2099-01-01",
    bootloader: str = "green",
    apps: list[dict] | None = None,
    logs: list[dict] | None = None,
) -> dict:
    root_detection = {
        "su_binary_found": rooted,
        "test_keys_found": False,
        "superuser_apk_found": False,
        "is_rooted": rooted,
    }
    return {
        "payload_id": payload_id,
        "scan_id": scan_id,
        "device_id": device_id,
        "created_at_epoch_ms": 1_700_000_000_000 + scan_id,
        "enrollment_token": enrollment_token,
        "device_report": {
            "device_id": device_id,
            "timestamp_epoch_ms": 1_700_000_000_000 + scan_id,
            "root_detection": root_detection,
            "integrity_verdict": integrity,
            "integrity_details": None,
            "integrity_error_code": None,
            "integrity_token_hash_sha256": None,
            "security_patch_date": patch_date,
            "bootloader_state": bootloader,
        },
        "app_snapshot": {
            "device_id": device_id,
            "timestamp_epoch_ms": 1_700_000_000_000 + scan_id,
            "total_app_count": len(apps or []),
            "is_delta": False,
            "apps": apps or [],
        },
        "important_logs": logs or [],
    }


def suspicious_app(package_name: str = "com.example.suspicious") -> dict:
    return {
        "package_name": package_name,
        "version_name": "1.0",
        "version_code": 1,
        "apk_sha256": "a" * 64,
        "cert_sha256": "b" * 64,
        "requested_permissions": ["android.permission.READ_SMS"],
        "install_source": "SIDELOADED",
        "is_system_app": False,
        "first_install_time": 1_700_000_000_000,
        "last_update_time": 1_700_000_000_000,
    }


def important_log(message: str = "token=secret permission denied for user@example.com") -> dict:
    return {
        "id": 1,
        "timestamp_epoch_ms": 1_700_000_000_000,
        "device_id": "sample-device-001",
        "tag": "Security",
        "level": "ERROR",
        "message": message,
        "matched_rule": "THREAT_REGEX",
    }
