from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from jsonschema import ValidationError
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.auth.bearer import verify_enrollment_token
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

    record, duplicate = ingestion_service.ingest(session, payload)
    return {
        "accepted": True,
        "duplicate": duplicate,
        "payload_id": record.payload_id,
        "processing_status": record.processing_status,
    }
