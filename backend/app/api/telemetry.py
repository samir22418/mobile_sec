from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from jsonschema import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.bearer import verify_enrollment_token
from app.dependencies import get_session
from app.models import TelemetryPayload
from app.services.ingestion import IngestionService
from app.services.validation import TelemetryValidationService, validation_error_message

router = APIRouter()

@router.post("/api/v1/telemetry", status_code=status.HTTP_202_ACCEPTED)
def ingest_telemetry(
    request: Request,
    payload: dict = Body(...),
    session: Session = Depends(get_session),
    token: str = Depends(verify_enrollment_token),
) -> dict:
    validator: TelemetryValidationService = request.app.state.telemetry_validator
    ingestion_service: IngestionService = request.app.state.ingestion_service

    try:
        validator.validate(payload)
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "invalid_schema", "message": validation_error_message(error)},
        ) from error

    existing = session.scalar(select(TelemetryPayload).where(TelemetryPayload.payload_id == payload["payload_id"]))
    if existing is not None:
        return {
            "accepted": True,
            "duplicate": True,
            "payload_id": existing.payload_id,
            "processing_status": existing.processing_status,
        }

    rate_limiter = request.app.state.telemetry_rate_limiter
    client_host = request.client.host if request.client else "unknown"
    rate_key = f"{payload['device_id']}:{client_host}"
    if not rate_limiter.allow(rate_key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "message": "Too many telemetry submissions. Try again later."},
        )

    record, duplicate = ingestion_service.ingest(session, payload)
    return {
        "accepted": True,
        "duplicate": duplicate,
        "payload_id": record.payload_id,
        "processing_status": record.processing_status,
    }
