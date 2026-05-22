from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from jsonschema import ValidationError
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.models import AnalystFeedback, RiskAssessment, TelemetryPayload
from app.services.auth import AuthError, AuthService
from app.services.ingestion import IngestionService
from app.services.validation import TelemetryValidationService, validation_error_message


router = APIRouter()


class FeedbackRequest(BaseModel):
    label: str
    payload_id: str | None = None
    analyst_id: str | None = None
    notes: str | None = None


ALLOWED_FEEDBACK_LABELS = {
    "TRUE_POSITIVE",
    "FALSE_POSITIVE",
    "BENIGN",
    "UNKNOWN",
    "NEEDS_MORE_DATA",
}


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": "aegis-backend"}


@router.post("/api/v1/telemetry", status_code=status.HTTP_202_ACCEPTED)
def ingest_telemetry(
    request: Request,
    payload: dict = Body(...),
    session: Session = Depends(get_session),
) -> dict:
    validator: TelemetryValidationService = request.app.state.telemetry_validator
    auth_service: AuthService = request.app.state.auth_service
    ingestion_service: IngestionService = request.app.state.ingestion_service

    try:
        validator.validate(payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_schema", "message": validation_error_message(error)},
        ) from error

    try:
        auth_service.authenticate_payload(payload)
    except AuthError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized", "message": str(error)},
        ) from error

    record, duplicate = ingestion_service.ingest(session, payload)
    return {
        "accepted": True,
        "duplicate": duplicate,
        "payload_id": record.payload_id,
        "processing_status": record.processing_status,
    }


@router.get("/api/v1/devices/{device_id}/latest-risk")
def latest_risk(device_id: str, session: Session = Depends(get_session)) -> dict:
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
def device_timeline(device_id: str, session: Session = Depends(get_session), limit: int = 20) -> dict:
    assessments = session.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.device_id == device_id)
        .order_by(desc(RiskAssessment.created_at), desc(RiskAssessment.id))
        .limit(min(max(limit, 1), 100))
    ).all()
    return {
        "device_id": device_id,
        "items": [risk_response(assessment) for assessment in assessments],
    }


@router.get("/api/v1/payloads/{payload_id}")
def payload_lookup(payload_id: str, session: Session = Depends(get_session)) -> dict:
    record = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload_id))
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    assessment = session.scalar(select(RiskAssessment).where(RiskAssessment.payload_id == payload_id))
    return {
        "payload_id": record.payload_id,
        "device_id": record.device_id,
        "scan_id": record.scan_id,
        "processing_status": record.processing_status,
        "processing_error": record.processing_error,
        "received_at": record.received_at.isoformat(),
        "risk": risk_response(assessment) if assessment else None,
    }


@router.post("/api/v1/findings/{finding_id}/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(
    finding_id: str,
    body: FeedbackRequest,
    session: Session = Depends(get_session),
) -> dict:
    if body.label not in ALLOWED_FEEDBACK_LABELS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_label", "allowed": sorted(ALLOWED_FEEDBACK_LABELS)},
        )
    feedback = AnalystFeedback(
        finding_id=finding_id,
        payload_id=body.payload_id,
        analyst_id=body.analyst_id,
        label=body.label,
        notes=body.notes,
    )
    session.add(feedback)
    session.commit()
    session.refresh(feedback)
    return {
        "id": feedback.id,
        "finding_id": feedback.finding_id,
        "payload_id": feedback.payload_id,
        "label": feedback.label,
        "created_at": feedback.created_at.isoformat(),
    }


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

