from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    label: str
    payload_id: str | None = None
    analyst_id: str | None = None
    notes: str | None = None
