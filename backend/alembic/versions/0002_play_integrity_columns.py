"""Add Play Integrity verification columns to device_reports.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "device_reports",
        sa.Column("verified_integrity_verdict", sa.String(64), nullable=True),
    )
    op.add_column(
        "device_reports",
        sa.Column("integrity_nonce", sa.String(500), nullable=True),
    )
    op.create_index(
        op.f("ix_device_reports_integrity_nonce"),
        "device_reports",
        ["integrity_nonce"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_device_reports_integrity_nonce"), table_name="device_reports")
    op.drop_column("device_reports", "integrity_nonce")
    op.drop_column("device_reports", "verified_integrity_verdict")
