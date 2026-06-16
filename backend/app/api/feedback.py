from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.bearer import verify_analyst_token
from app.dependencies import get_session
from app.models import AnalystFeedback
from app.schemas.feedback import FeedbackRequest

router = APIRouter()

ALLOWED_FEEDBACK_LABELS = {
    "TRUE_POSITIVE",
    "FALSE_POSITIVE",
    "BENIGN",
    "UNKNOWN",
    "NEEDS_MORE_DATA",
}

@router.post("/api/v1/findings/{finding_id}/feedback", status_code=status.HTTP_201_CREATED)
def create_feedback(
    finding_id: str,
    body: FeedbackRequest,
    session: Session = Depends(get_session),
    token: str = Depends(verify_analyst_token),
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
