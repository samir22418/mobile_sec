from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AIModelRun(Base):
    __tablename__ = "ai_model_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), index=True)
    model_role: Mapped[str] = mapped_column(String(64))
    provider: Mapped[str] = mapped_column(String(64), default="unknown")
    model_name: Mapped[str] = mapped_column(String(128))
    prompt_version: Mapped[str] = mapped_column(String(64))
    input_bundle_hash: Mapped[str] = mapped_column(String(64))
    output_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIRiskDecision(Base):
    __tablename__ = "ai_risk_decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), unique=True, index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    deterministic_score: Mapped[int] = mapped_column(Integer)
    deterministic_label: Mapped[str] = mapped_column(String(32))
    final_score: Mapped[int] = mapped_column(Integer)
    final_label: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    reasons_json: Mapped[str] = mapped_column(Text)
    evidence_refs_json: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(Text)
    used_ai_final: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="SUCCEEDED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIEvidenceBundle(Base):
    __tablename__ = "ai_evidence_bundles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    bundle_stage: Mapped[str] = mapped_column(String(64))
    bundle_hash: Mapped[str] = mapped_column(String(64), index=True)
    router_path: Mapped[str] = mapped_column(String(64), default="rules_only")
    bundle_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AIFinding(Base):
    __tablename__ = "ai_findings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    model_run_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ai_model_runs.id"), nullable=True, index=True)
    source_role: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str] = mapped_column(Text)
    evidence_refs_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), default="AEGIS AI chat")
    analyst_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    context_payload_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="SUCCEEDED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ChatAction(Base):
    __tablename__ = "chat_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(64), ForeignKey("chat_sessions.id"), index=True)
    message_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("chat_messages.id"), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(128))
    payload_json: Mapped[str] = mapped_column(Text)
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    analyst_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
