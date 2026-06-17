from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TelemetryPayload(Base):
    __tablename__ = "telemetry_payloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    scan_id: Mapped[int] = mapped_column(Integer)
    payload_created_at_epoch_ms: Mapped[int] = mapped_column(BigInteger)
    schema_version: Mapped[str] = mapped_column(String(32), default="v1")
    raw_payload_path: Mapped[str] = mapped_column(Text)
    processing_status: Mapped[str] = mapped_column(String(32), default="ACCEPTED", index=True)
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class DeviceReport(Base):
    __tablename__ = "device_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), unique=True, index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    observed_at_epoch_ms: Mapped[int] = mapped_column(BigInteger)
    is_rooted: Mapped[bool] = mapped_column(Boolean)
    root_signal_count: Mapped[int] = mapped_column(Integer)
    su_binary_found: Mapped[bool] = mapped_column(Boolean)
    test_keys_found: Mapped[bool] = mapped_column(Boolean)
    superuser_apk_found: Mapped[bool] = mapped_column(Boolean)
    integrity_verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    verified_integrity_verdict: Mapped[str | None] = mapped_column(String(64), nullable=True)
    integrity_nonce: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    security_patch_date: Mapped[str] = mapped_column(String(32))
    security_patch_age_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bootloader_state: Mapped[str] = mapped_column(String(64))


class AppInventoryCurrent(Base):
    __tablename__ = "app_inventory_current"
    __table_args__ = (UniqueConstraint("device_id", "package_name", name="uq_device_package"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    package_name: Mapped[str] = mapped_column(String(255), index=True)
    version_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version_code: Mapped[int] = mapped_column(BigInteger)
    apk_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cert_sha256: Mapped[str | None] = mapped_column(String(128), nullable=True)
    install_source: Mapped[str] = mapped_column(String(64))
    is_system_app: Mapped[bool] = mapped_column(Boolean)
    requested_permissions_json: Mapped[str] = mapped_column(Text)
    first_install_time: Mapped[int] = mapped_column(BigInteger)
    last_update_time: Mapped[int] = mapped_column(BigInteger)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), index=True)


class ImportantLog(Base):
    __tablename__ = "important_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    payload_id: Mapped[str] = mapped_column(String(128), ForeignKey("telemetry_payloads.payload_id"), index=True)
    device_id: Mapped[str] = mapped_column(String(255), index=True)
    observed_at_epoch_ms: Mapped[int] = mapped_column(BigInteger)
    tag: Mapped[str] = mapped_column(String(128))
    level: Mapped[str] = mapped_column(String(32))
    matched_rule: Mapped[str] = mapped_column(String(64))
    message_redacted: Mapped[str] = mapped_column(Text)
    message_hash: Mapped[str] = mapped_column(String(64), index=True)
