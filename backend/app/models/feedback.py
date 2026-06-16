from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalystFeedback(Base):
    __tablename__ = "analyst_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    finding_id: Mapped[str] = mapped_column(String(128), index=True)
    payload_id: Mapped[str | None] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), nullable=True, index=True)
    analyst_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    label: Mapped[str] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
