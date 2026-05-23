import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.auth.bearer import verify_analyst_token
from app.models import RiskAssessment, TelemetryPayload

router = APIRouter()

def risk_response(assessment: RiskAssessment | None) -> dict | None:
    if assessment is None:
        return None
    return {
        "payload_id": assessment.payload_id,
        "device_id": assessment.device_id,
        "risk_score": assessment.risk_score,
        "risk_label": assessment.risk_label,
        "confidence": assessment.confidence,
        "reasons": json.loads(assessment.reasons_json),
        "recommended_action": assessment.recommended_action,
        "needs_human_review": assessment.needs_human_review,
        "created_at": assessment.created_at.isoformat(),
    }
@router.get("/api/v1/devices")
def get_devices(
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    from app.models import TelemetryPayload
    from sqlalchemy import func
    
    # Simple distinct device list for now
    devices = session.scalars(select(TelemetryPayload.device_id).distinct()).all()
    
    results = []
    for device_id in devices:
        # Get count
        count = session.scalar(select(func.count(TelemetryPayload.id)).where(TelemetryPayload.device_id == device_id))
        
        # Get latest risk
        risk = session.scalar(
            select(RiskAssessment)
            .where(RiskAssessment.device_id == device_id)
            .order_by(desc(RiskAssessment.created_at))
            .limit(1)
        )
        
        results.append({
            "device_id": device_id,
            "payload_count": count or 0,
            "latest_risk_label": risk.risk_label if risk else "UNKNOWN",
            "latest_risk_score": risk.risk_score if risk else 0
        })
        
    return {"items": results}

@router.get("/api/v1/devices/{device_id}/latest-risk")
def latest_risk(
    device_id: str, 
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
) -> dict:
    assessment = session.scalar(
        select(RiskAssessment)
        .where(RiskAssessment.device_id == device_id)
        .order_by(desc(RiskAssessment.created_at), desc(RiskAssessment.id))
        .limit(1)
    )
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    return risk_response(assessment)

@router.get("/api/v1/devices/{device_id}/timeline")
def device_timeline(
    device_id: str, 
    session: Session = Depends(get_session), 
    limit: int = 20,
    token: str = Depends(verify_analyst_token),
) -> dict:
    records = session.scalars(
        select(TelemetryPayload)
        .where(TelemetryPayload.device_id == device_id)
        .order_by(desc(TelemetryPayload.payload_created_at_epoch_ms), desc(TelemetryPayload.id))
        .limit(min(max(limit, 1), 100))
    ).all()
    items = []
    for record in records:
        assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == record.payload_id))
        item = {
            "payload_id": record.payload_id,
            "device_id": record.device_id,
            "scan_id": record.scan_id,
            "created_at_epoch_ms": record.payload_created_at_epoch_ms,
            "processing_status": record.processing_status,
            "received_at": record.received_at.isoformat(),
            "risk": risk_response(assessment) if assessment else None,
        }
        if assessment is not None:
            item.update(risk_response(assessment) or {})
        items.append(item)
    return {
        "device_id": device_id,
        "items": items,
    }
