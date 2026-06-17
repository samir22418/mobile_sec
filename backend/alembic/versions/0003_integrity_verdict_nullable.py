"""Make device_reports.integrity_verdict nullable.

Play Integrity collection has been removed from the Android agent.
Existing rows retain their values; new rows from updated agents will
store NULL.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("device_reports") as batch_op:
        batch_op.alter_column(
            "integrity_verdict",
            existing_type=sa.String(64),
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("device_reports") as batch_op:
        batch_op.alter_column(
            "integrity_verdict",
            existing_type=sa.String(64),
            nullable=False,
        )
