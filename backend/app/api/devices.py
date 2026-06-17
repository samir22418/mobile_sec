from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.auth.bearer import verify_analyst_token
from app.dependencies import get_session
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
    # 1 query: payload counts per device
    count_rows = session.execute(
        select(TelemetryPayload.device_id, func.count(TelemetryPayload.id).label("n"))
        .group_by(TelemetryPayload.device_id)
    ).all()

    if not count_rows:
        return {"items": []}

    device_ids = [r.device_id for r in count_rows]
    counts: dict[str, int] = {r.device_id: r.n for r in count_rows}

    # 1 query: latest risk assessment per device via max(id) subquery
    latest_id_subq = (
        select(
            RiskAssessment.device_id,
            func.max(RiskAssessment.id).label("max_id"),
        )
        .where(RiskAssessment.device_id.in_(device_ids))
        .group_by(RiskAssessment.device_id)
        .subquery()
    )
    risks: dict[str, RiskAssessment] = {
        r.device_id: r
        for r in session.scalars(
            select(RiskAssessment).join(
                latest_id_subq,
                (RiskAssessment.device_id == latest_id_subq.c.device_id)
                & (RiskAssessment.id == latest_id_subq.c.max_id),
            )
        ).all()
    }

    results = [
        {
            "device_id": did,
            "payload_count": counts[did],
            "latest_risk_label": risks[did].risk_label if did in risks else "UNKNOWN",
            "latest_risk_score": risks[did].risk_score if did in risks else 0,
        }
        for did in device_ids
    ]
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
    return risk_response(assessment) or {}


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
        .order_by(
            desc(TelemetryPayload.payload_created_at_epoch_ms),
            desc(TelemetryPayload.id),
        )
        .limit(min(max(limit, 1), 100))
    ).all()

    # 1 query for all risk assessments in this timeline page
    payload_ids = [r.payload_id for r in records]
    assessments: dict[str, RiskAssessment] = (
        {
            a.payload_id: a
            for a in session.scalars(
                select(RiskAssessment).where(RiskAssessment.payload_id.in_(payload_ids))
            ).all()
        }
        if payload_ids
        else {}
    )

    items = []
    for record in records:
        assessment = assessments.get(record.payload_id)
        item: dict = {
            "payload_id": record.payload_id,
            "device_id": record.device_id,
            "scan_id": record.scan_id,
            "created_at_epoch_ms": record.payload_created_at_epoch_ms,
            "processing_status": record.processing_status,
            "received_at": record.received_at.isoformat(),
            "risk": risk_response(assessment),
        }
        if assessment is not None:
            item.update(risk_response(assessment) or {})
        items.append(item)
    return {
        "device_id": device_id,
        "items": items,
    }
