import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.auth.bearer import verify_analyst_token
from app.models import (
    AIModelRun,
    AppInventoryCurrent,
    DeviceReport,
    ImportantLog,
    RiskAssessment,
    TelemetryPayload,
)
from app.api.devices import risk_response

router = APIRouter()

@router.get("/api/v1/payloads/{payload_id}")
def payload_lookup(
    payload_id: str, 
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    record = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == payload_id))
    device_report = session.scalar(select(DeviceReport).where(DeviceReport.payload_id == payload_id))
    apps = session.scalars(
        select(AppInventoryCurrent).where(AppInventoryCurrent.device_id == record.device_id)
    ).all()
    logs = session.scalars(select(ImportantLog).where(ImportantLog.payload_id == payload_id)).all()
    ai_runs = session.scalars(select(AIModelRun).where(AIModelRun.payload_id == payload_id)).all()
    risk = risk_response(assessment) if assessment else None
    return {
        "payload_id": record.payload_id,
        "device_id": record.device_id,
        "scan_id": record.scan_id,
        "processing_status": record.processing_status,
        "processing_error": record.processing_error,
        "received_at": record.received_at.isoformat(),
        "created_at_epoch_ms": record.payload_created_at_epoch_ms,
        "device_report": serialize_device_report(device_report),
        "risk": risk,
        "risk_assessment": risk,
        "apps": [serialize_app(app) for app in apps],
        "logs": [serialize_log(log) for log in logs],
        "ai_runs": [serialize_ai_run(run) for run in ai_runs],
    }


def serialize_device_report(report: DeviceReport | None) -> dict | None:
    if report is None:
        return None
    return {
        "is_rooted": report.is_rooted,
        "root_signal_count": report.root_signal_count,
        "play_integrity_status": report.integrity_verdict,
        "security_patch_date": report.security_patch_date,
        "security_patch_age_days": report.security_patch_age_days,
        "bootloader_state": report.bootloader_state,
    }


def serialize_app(app: AppInventoryCurrent) -> dict:
    permissions = json.loads(app.requested_permissions_json)
    suspicious_permissions = {
        "android.permission.READ_SMS",
        "android.permission.SEND_SMS",
        "android.permission.READ_CONTACTS",
        "android.permission.RECORD_AUDIO",
        "android.permission.CAMERA",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.BIND_ACCESSIBILITY_SERVICE",
    }
    return {
        "package_name": app.package_name,
        "version_name": app.version_name,
        "version_code": app.version_code,
        "install_source": app.install_source,
        "installer_package": app.install_source,
        "is_system_app": app.is_system_app,
        "requested_permissions": permissions,
        "is_suspicious": app.install_source in {"SIDELOADED", "UNKNOWN"}
        and bool(suspicious_permissions.intersection(permissions)),
        "last_seen_payload_id": app.last_seen_payload_id,
    }


def serialize_log(log: ImportantLog) -> dict:
    return {
        "id": log.id,
        "tag": log.tag,
        "level": log.level,
        "matched_rule": log.matched_rule,
        "message_redacted": log.message_redacted,
        "message_hash": log.message_hash,
        "observed_at_epoch_ms": log.observed_at_epoch_ms,
    }


def serialize_ai_run(run: AIModelRun) -> dict:
    output = json.loads(run.output_json)
    findings = output.get("findings") if isinstance(output, dict) else []
    first_finding = findings[0] if findings else {}
    return {
        "id": run.id,
        "model_role": run.model_role,
        "model_used": run.model_name,
        "model_name": run.model_name,
        "prompt_version": run.prompt_version,
        "status": run.status,
        "finding_summary": first_finding.get("title") or output.get("risk_label") or run.status,
        "confidence_score": int(float(output.get("confidence", 0)) * 100) if isinstance(output, dict) else 0,
        "output": output,
        "created_at": run.created_at.isoformat(),
    }
