from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIModelRun(Base):
    __tablename__ = "ai_model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), index=True)
    model_role: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))
    input_bundle_hash: Mapped[str] = mapped_column(String(64))
    output_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
