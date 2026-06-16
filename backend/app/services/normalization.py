from __future__ import annotations

import json
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import AppInventoryCurrent, DeviceReport, ImportantLog
from app.services.redaction import RedactionService


class NormalizationService:
    def __init__(self, redaction: RedactionService | None = None) -> None:
        self.redaction = redaction or RedactionService()

    def normalize(self, session: Session, payload: dict) -> None:
        payload_id = payload["payload_id"]
        device_id = payload["device_id"]
        self._normalize_device_report(session, payload_id, device_id, payload["device_report"])
        self._normalize_apps(session, payload_id, device_id, payload["app_snapshot"])
        self._normalize_logs(session, payload_id, device_id, payload.get("important_logs", []))

    def _normalize_device_report(self, session: Session, payload_id: str, device_id: str, report: dict) -> None:
        session.execute(delete(DeviceReport).where(DeviceReport.payload_id == payload_id))
        root = report.get("root_detection", {})
        root_flags = [
            bool(root.get("su_binary_found")),
            bool(root.get("test_keys_found")),
            bool(root.get("superuser_apk_found")),
        ]
        session.add(
            DeviceReport(
                payload_id=payload_id,
                device_id=device_id,
                observed_at_epoch_ms=report["timestamp_epoch_ms"],
                is_rooted=bool(root.get("is_rooted")),
                root_signal_count=sum(1 for flag in root_flags if flag),
                su_binary_found=root_flags[0],
                test_keys_found=root_flags[1],
                superuser_apk_found=root_flags[2],
                integrity_verdict=report["integrity_verdict"],
                integrity_nonce=report.get("integrity_nonce"),
                security_patch_date=report["security_patch_date"],
                security_patch_age_days=patch_age_days(report.get("security_patch_date")),
                bootloader_state=report["bootloader_state"],
            )
        )

    def _normalize_apps(self, session: Session, payload_id: str, device_id: str, snapshot: dict) -> None:
        now_apps = snapshot.get("apps", [])
        if not snapshot.get("is_delta", False):
            session.execute(delete(AppInventoryCurrent).where(AppInventoryCurrent.device_id == device_id))
        for app in now_apps:
            existing = session.scalar(
                select(AppInventoryCurrent).where(
                    AppInventoryCurrent.device_id == device_id,
                    AppInventoryCurrent.package_name == app["package_name"],
                )
            )
            permissions_json = json.dumps(app.get("requested_permissions", []), sort_keys=True)
            if existing is None:
                existing = AppInventoryCurrent(
                    device_id=device_id,
                    package_name=app["package_name"],
                    version_name=app.get("version_name"),
                    version_code=app["version_code"],
                    apk_sha256=app.get("apk_sha256"),
                    cert_sha256=app.get("cert_sha256"),
                    install_source=app["install_source"],
                    is_system_app=bool(app["is_system_app"]),
                    requested_permissions_json=permissions_json,
                    first_install_time=app["first_install_time"],
                    last_update_time=app["last_update_time"],
                    last_seen_payload_id=payload_id,
                )
                session.add(existing)
            else:
                existing.version_name = app.get("version_name")
                existing.version_code = app["version_code"]
                existing.apk_sha256 = app.get("apk_sha256")
                existing.cert_sha256 = app.get("cert_sha256")
                existing.install_source = app["install_source"]
                existing.is_system_app = bool(app["is_system_app"])
                existing.requested_permissions_json = permissions_json
                existing.first_install_time = app["first_install_time"]
                existing.last_update_time = app["last_update_time"]
                existing.last_seen_payload_id = payload_id

    def _normalize_logs(self, session: Session, payload_id: str, device_id: str, logs: list[dict]) -> None:
        session.execute(delete(ImportantLog).where(ImportantLog.payload_id == payload_id))
        for log in logs:
            original = log["message"]
            session.add(
                ImportantLog(
                    payload_id=payload_id,
                    device_id=device_id,
                    observed_at_epoch_ms=log["timestamp_epoch_ms"],
                    tag=log["tag"],
                    level=log["level"],
                    matched_rule=log["matched_rule"],
                    message_redacted=self.redaction.redact(original),
                    message_hash=self.redaction.hash_message(original),
                )
            )


def patch_age_days(value: str | None) -> int | None:
    if not value or value == "unknown":
        return None
    try:
        patch_date = date.fromisoformat(value)
    except ValueError:
        return None
    delta = date.today() - patch_date
    return max(delta.days, 0)

