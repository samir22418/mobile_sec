from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.auth.bearer import verify_analyst_token
from app.dependencies import get_session
from app.models import EnrollmentToken
from app.schemas.enrollment import EnrollmentTokenCreateRequest
from app.services.enrollment_tokens import EnrollmentTokenService

router = APIRouter()


@router.post("/api/v1/enrollment-tokens", status_code=status.HTTP_201_CREATED)
def create_enrollment_token(
    body: EnrollmentTokenCreateRequest,
    session: Session = Depends(get_session),
    analyst_token: str = Depends(verify_analyst_token),
) -> dict:
    record, token = EnrollmentTokenService().create(
        session,
        label=body.label,
        device_id=body.device_id,
        created_by="analyst",
        expires_at=body.expires_at,
    )
    return serialize_token(record) | {"token": token}


@router.get("/api/v1/enrollment-tokens")
def list_enrollment_tokens(
    session: Session = Depends(get_session),
    analyst_token: str = Depends(verify_analyst_token),
) -> dict:
    records = session.scalars(
        select(EnrollmentToken).order_by(desc(EnrollmentToken.created_at), desc(EnrollmentToken.id))
    ).all()
    return {"items": [serialize_token(record) for record in records]}


@router.post("/api/v1/enrollment-tokens/{token_id}/revoke")
def revoke_enrollment_token(
    token_id: int,
    session: Session = Depends(get_session),
    analyst_token: str = Depends(verify_analyst_token),
) -> dict:
    record = EnrollmentTokenService().revoke(session, token_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    return serialize_token(record)


def serialize_token(record: EnrollmentToken) -> dict:
    return {
        "id": record.id,
        "label": record.label,
        "device_id": record.device_id,
        "is_active": record.is_active,
        "created_at": record.created_at.isoformat(),
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
        "last_used_at": record.last_used_at.isoformat() if record.last_used_at else None,
    }
