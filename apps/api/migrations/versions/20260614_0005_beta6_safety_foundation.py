"""Add Beta-6 safety foundation metadata.

Revision ID: 20260614_0005
Revises: 20260614_0004
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20260614_0005"
down_revision = "20260614_0004"
branch_labels = None
depends_on = None


def _column_names(table_name: str) -> set[str]:
    return {item["name"] for item in inspect(op.get_bind()).get_columns(table_name)}


def upgrade() -> None:
    batch_columns = _column_names("import_batches")
    if "compensated_at" not in batch_columns:
        op.add_column("import_batches", sa.Column("compensated_at", sa.DateTime(timezone=True), nullable=True))
    if "compensation_reason" not in batch_columns:
        op.add_column("import_batches", sa.Column("compensation_reason", sa.Text(), nullable=True))
    if "compensation_transaction_ids" not in batch_columns:
        op.add_column(
            "import_batches",
            sa.Column("compensation_transaction_ids", sa.JSON(), nullable=False, server_default="[]"),
        )

    tables = set(inspect(op.get_bind()).get_table_names())
    if "safety_events" not in tables:
        op.create_table(
            "safety_events",
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("artifact_name", sa.Text(), nullable=False),
            sa.Column("artifact_path", sa.Text(), nullable=False),
            sa.Column("artifact_sha256", sa.String(length=64), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("actor", sa.String(length=120), nullable=True),
            sa.Column("event_metadata", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "event_type IN ('BACKUP_CREATED', 'RESTORE_COMPLETED')",
                name="ck_safety_events_type",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(op.f("ix_safety_events_event_type"), "safety_events", ["event_type"], unique=False)
        op.create_index(op.f("ix_safety_events_artifact_sha256"), "safety_events", ["artifact_sha256"], unique=False)


def downgrade() -> None:
    raise RuntimeError("Beta-6 safety foundation migration is not safely reversible.")
