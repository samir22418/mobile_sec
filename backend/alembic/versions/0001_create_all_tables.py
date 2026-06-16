"""Create all tables from scratch

Revision ID: 0001
Revises:
Create Date: 2026-06-15 00:00:00.000000

Replaces the two broken migrations that assumed create_all() had already run.
This migration creates all 14 tables with proper FK constraints inline.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Core telemetry (no FK) ────────────────────────────────────────────────
    op.create_table(
        "telemetry_payloads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("payload_created_at_epoch_ms", sa.BigInteger(), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False, server_default="v1"),
        sa.Column("raw_payload_path", sa.Text(), nullable=False),
        sa.Column("processing_status", sa.String(32), nullable=False, server_default="ACCEPTED"),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_id"),
    )
    op.create_index("ix_telemetry_payloads_payload_id", "telemetry_payloads", ["payload_id"], unique=True)
    op.create_index("ix_telemetry_payloads_device_id", "telemetry_payloads", ["device_id"])
    op.create_index("ix_telemetry_payloads_processing_status", "telemetry_payloads", ["processing_status"])

    # ── Enrollment (no FK) ───────────────────────────────────────────────────
    op.create_table(
        "enrollment_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_enrollment_tokens_token_hash", "enrollment_tokens", ["token_hash"], unique=True)
    op.create_index("ix_enrollment_tokens_device_id", "enrollment_tokens", ["device_id"])
    op.create_index("ix_enrollment_tokens_is_active", "enrollment_tokens", ["is_active"])

    # ── Device reports (FK: telemetry_payloads) ───────────────────────────────
    op.create_table(
        "device_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("observed_at_epoch_ms", sa.BigInteger(), nullable=False),
        sa.Column("is_rooted", sa.Boolean(), nullable=False),
        sa.Column("root_signal_count", sa.Integer(), nullable=False),
        sa.Column("su_binary_found", sa.Boolean(), nullable=False),
        sa.Column("test_keys_found", sa.Boolean(), nullable=False),
        sa.Column("superuser_apk_found", sa.Boolean(), nullable=False),
        sa.Column("integrity_verdict", sa.String(64), nullable=False),
        sa.Column("security_patch_date", sa.String(32), nullable=False),
        sa.Column("security_patch_age_days", sa.Integer(), nullable=True),
        sa.Column("bootloader_state", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_id"),
    )
    op.create_index("ix_device_reports_payload_id", "device_reports", ["payload_id"], unique=True)
    op.create_index("ix_device_reports_device_id", "device_reports", ["device_id"])

    # ── App inventory (FK: telemetry_payloads) ────────────────────────────────
    op.create_table(
        "app_inventory_current",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("package_name", sa.String(255), nullable=False),
        sa.Column("version_name", sa.String(128), nullable=True),
        sa.Column("version_code", sa.BigInteger(), nullable=False),
        sa.Column("apk_sha256", sa.String(128), nullable=True),
        sa.Column("cert_sha256", sa.String(128), nullable=True),
        sa.Column("install_source", sa.String(64), nullable=False),
        sa.Column("is_system_app", sa.Boolean(), nullable=False),
        sa.Column("requested_permissions_json", sa.Text(), nullable=False),
        sa.Column("first_install_time", sa.BigInteger(), nullable=False),
        sa.Column("last_update_time", sa.BigInteger(), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_payload_id", sa.String(128), nullable=False),
        sa.ForeignKeyConstraint(["last_seen_payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "package_name", name="uq_device_package"),
    )
    op.create_index("ix_app_inventory_current_device_id", "app_inventory_current", ["device_id"])
    op.create_index("ix_app_inventory_current_package_name", "app_inventory_current", ["package_name"])
    op.create_index("ix_app_inventory_current_last_seen_payload_id", "app_inventory_current", ["last_seen_payload_id"])

    # ── Important logs (FK: telemetry_payloads) ───────────────────────────────
    op.create_table(
        "important_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("observed_at_epoch_ms", sa.BigInteger(), nullable=False),
        sa.Column("tag", sa.String(128), nullable=False),
        sa.Column("level", sa.String(32), nullable=False),
        sa.Column("matched_rule", sa.String(64), nullable=False),
        sa.Column("message_redacted", sa.Text(), nullable=False),
        sa.Column("message_hash", sa.String(64), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_important_logs_payload_id", "important_logs", ["payload_id"])
    op.create_index("ix_important_logs_device_id", "important_logs", ["device_id"])
    op.create_index("ix_important_logs_message_hash", "important_logs", ["message_hash"])

    # ── Risk assessments (FK: telemetry_payloads) ─────────────────────────────
    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_label", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("needs_human_review", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_id"),
    )
    op.create_index("ix_risk_assessments_payload_id", "risk_assessments", ["payload_id"], unique=True)
    op.create_index("ix_risk_assessments_device_id", "risk_assessments", ["device_id"])

    # ── Analyst feedback (FK: telemetry_payloads) ─────────────────────────────
    op.create_table(
        "analyst_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("finding_id", sa.String(128), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=True),
        sa.Column("analyst_id", sa.String(128), nullable=True),
        sa.Column("label", sa.String(64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analyst_feedback_finding_id", "analyst_feedback", ["finding_id"])
    op.create_index("ix_analyst_feedback_payload_id", "analyst_feedback", ["payload_id"])

    # ── AI model runs (FK: telemetry_payloads) ────────────────────────────────
    op.create_table(
        "ai_model_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("model_role", sa.String(64), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False, server_default="unknown"),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("input_bundle_hash", sa.String(64), nullable=False),
        sa.Column("output_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_estimate", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_model_runs_payload_id", "ai_model_runs", ["payload_id"])

    # ── AI risk decisions (FK: telemetry_payloads) ────────────────────────────
    op.create_table(
        "ai_risk_decisions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("deterministic_score", sa.Integer(), nullable=False),
        sa.Column("deterministic_label", sa.String(32), nullable=False),
        sa.Column("final_score", sa.Integer(), nullable=False),
        sa.Column("final_label", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("evidence_refs_json", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("used_ai_final", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("status", sa.String(32), nullable=False, server_default="SUCCEEDED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payload_id"),
    )
    op.create_index("ix_ai_risk_decisions_payload_id", "ai_risk_decisions", ["payload_id"], unique=True)
    op.create_index("ix_ai_risk_decisions_device_id", "ai_risk_decisions", ["device_id"])

    # ── AI evidence bundles (FK: telemetry_payloads) ──────────────────────────
    op.create_table(
        "ai_evidence_bundles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("bundle_stage", sa.String(64), nullable=False),
        sa.Column("bundle_hash", sa.String(64), nullable=False),
        sa.Column("router_path", sa.String(64), nullable=False, server_default="rules_only"),
        sa.Column("bundle_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_evidence_bundles_payload_id", "ai_evidence_bundles", ["payload_id"])
    op.create_index("ix_ai_evidence_bundles_device_id", "ai_evidence_bundles", ["device_id"])
    op.create_index("ix_ai_evidence_bundles_bundle_hash", "ai_evidence_bundles", ["bundle_hash"])

    # ── AI findings (FK: telemetry_payloads + ai_model_runs) ─────────────────
    op.create_table(
        "ai_findings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payload_id", sa.String(128), nullable=False),
        sa.Column("device_id", sa.String(255), nullable=False),
        sa.Column("model_run_id", sa.Integer(), nullable=True),
        sa.Column("source_role", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_refs_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="OPEN"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payload_id"], ["telemetry_payloads.payload_id"]),
        sa.ForeignKeyConstraint(["model_run_id"], ["ai_model_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ai_findings_payload_id", "ai_findings", ["payload_id"])
    op.create_index("ix_ai_findings_device_id", "ai_findings", ["device_id"])
    op.create_index("ix_ai_findings_model_run_id", "ai_findings", ["model_run_id"])

    # ── Chat sessions (no FK) ─────────────────────────────────────────────────
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False, server_default="AEGIS AI chat"),
        sa.Column("analyst_token_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Chat messages (FK: chat_sessions) ─────────────────────────────────────
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("context_payload_id", sa.String(128), nullable=True),
        sa.Column("model_name", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="SUCCEEDED"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])
    op.create_index("ix_chat_messages_context_payload_id", "chat_messages", ["context_payload_id"])

    # ── Chat actions (FK: chat_sessions + chat_messages) ──────────────────────
    op.create_table(
        "chat_actions",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("message_id", sa.String(64), nullable=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
        sa.Column("analyst_token_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["chat_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_actions_session_id", "chat_actions", ["session_id"])
    op.create_index("ix_chat_actions_message_id", "chat_actions", ["message_id"])


def downgrade() -> None:
    op.drop_table("chat_actions")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("ai_findings")
    op.drop_table("ai_evidence_bundles")
    op.drop_table("ai_risk_decisions")
    op.drop_table("ai_model_runs")
    op.drop_table("analyst_feedback")
    op.drop_table("risk_assessments")
    op.drop_table("important_logs")
    op.drop_table("app_inventory_current")
    op.drop_table("device_reports")
    op.drop_table("enrollment_tokens")
    op.drop_table("telemetry_payloads")
