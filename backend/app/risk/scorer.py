from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import AppInventoryCurrent, DeviceReport, ImportantLog, RiskAssessment

SENSITIVE_PERMISSIONS = {
    "android.permission.READ_SMS",
    "android.permission.SEND_SMS",
    "android.permission.READ_CONTACTS",
    "android.permission.RECORD_AUDIO",
    "android.permission.CAMERA",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
}


class RiskScoringService:
    def score(self, session: Session, payload_id: str, device_id: str) -> RiskAssessment:
        existing = session.query(RiskAssessment).filter_by(payload_id=payload_id).one_or_none()
        if existing is not None:
            return existing

        device_report = session.query(DeviceReport).filter_by(payload_id=payload_id).one()
        apps = session.query(AppInventoryCurrent).filter_by(device_id=device_id).all()
        logs = session.query(ImportantLog).filter_by(payload_id=payload_id).all()

        score = 10
        reasons: list[str] = []

        if device_report.is_rooted:
            score += 35
            reasons.append("Root indicators were detected.")

        effective_verdict = device_report.verified_integrity_verdict or device_report.integrity_verdict
        verified = device_report.verified_integrity_verdict is not None

        match effective_verdict:
            case None:
                pass  # No integrity data sent — device not penalized
            case "FAILS":
                score += 35
                if verified:
                    reasons.append("Play Integrity backend-verified: device failed all integrity checks.")
                else:
                    reasons.append("Play Integrity failed.")
            case "REQUIRES_BACKEND_VERIFICATION":
                score += 18
                reasons.append("Play Integrity requires backend verification.")
            case "NOT_CONFIGURED":
                score += 18
                reasons.append("Play Integrity is not configured.")
            case "UNAVAILABLE" | "API_ERROR":
                score += 16
                reasons.append("Play Integrity did not produce a usable verdict.")
            case "MEETS_BASIC_INTEGRITY":
                score += 10
                if verified:
                    reasons.append("Play Integrity backend-verified: only basic integrity confirmed.")
                else:
                    reasons.append("Only basic Play Integrity is available.")
            case "MEETS_DEVICE_INTEGRITY" | "MEETS_STRONG_INTEGRITY":
                if verified:
                    reasons.append(f"Play Integrity backend-verified: {effective_verdict}.")

        if device_report.bootloader_state in {"orange", "red"}:
            score += 20
            reasons.append(f"Bootloader verified boot state is {device_report.bootloader_state}.")

        if device_report.security_patch_age_days is not None and device_report.security_patch_age_days > 90:
            score += 10
            reasons.append("Security patch appears older than 90 days.")

        sideloaded_sensitive_apps = [
            app for app in apps
            if app.install_source in {"SIDELOADED", "UNKNOWN"}
            and SENSITIVE_PERMISSIONS.intersection(json.loads(app.requested_permissions_json))
        ]
        if sideloaded_sensitive_apps:
            score += min(20, 8 + len(sideloaded_sensitive_apps) * 4)
            reasons.append(f"{len(sideloaded_sensitive_apps)} sideloaded or unknown-source app(s) request sensitive permissions.")

        if len(logs) >= 10:
            score += 12
            reasons.append(f"Important log volume is elevated: {len(logs)} entries.")
        elif logs:
            score += 5
            reasons.append(f"Important logs were captured: {len(logs)} entries.")

        bounded_score = max(0, min(score, 100))
        label = risk_label(bounded_score)
        assessment = RiskAssessment(
            payload_id=payload_id,
            device_id=device_id,
            risk_score=bounded_score,
            risk_label=label,
            confidence=confidence_for(bounded_score, reasons),
            reasons_json=json.dumps(reasons or ["No notable backend risk signals."], sort_keys=True),
            recommended_action=recommended_action(label, device_report.is_rooted),
            needs_human_review=bounded_score >= 50,
        )
        session.add(assessment)
        return assessment


def risk_label(score: int) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Watch"
    return "Low"


def confidence_for(score: int, reasons: list[str]) -> float:
    if score >= 75:
        return 0.9
    if score >= 50:
        return 0.82
    if reasons:
        return 0.72
    return 0.65


def recommended_action(label: str, is_rooted: bool) -> str:
    if label == "Critical":
        return "Quarantine or restrict the device until reviewed."
    if label == "High":
        return "Review the evidence and verify device trust before granting access."
    if is_rooted:
        return "Review root indicators before trusting this device."
    if label == "Watch":
        return "Monitor this device and review suspicious app or log evidence."
    return "No immediate action needed."

