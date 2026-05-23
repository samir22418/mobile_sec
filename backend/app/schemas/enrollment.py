from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class EnrollmentTokenCreateRequest(BaseModel):
    label: str = Field(default="New device", min_length=1, max_length=128)
    device_id: str | None = Field(default=None, max_length=255)
    expires_at: datetime | None = None


class EnrollmentTokenCreateResponse(BaseModel):
    id: int
    label: str
    device_id: str | None
    token: str
    is_active: bool
    created_at: str
    expires_at: str | None
