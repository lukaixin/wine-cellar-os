"""Add import batch audit tables.

Revision ID: 20260613_0002
Revises: 20260613_0001
Create Date: 2026-06-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20260613_0002"
down_revision = "20260613_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    if "import_batches" not in existing_tables:
        op.create_table(
            "import_batches",
            sa.Column("source_filename", sa.Text(), nullable=False),
            sa.Column("sheet_name", sa.String(length=120), nullable=False),
            sa.Column("file_sha256", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("row_count", sa.Integer(), nullable=False),
            sa.Column("valid_rows", sa.Integer(), nullable=False),
            sa.Column("invalid_rows", sa.Integer(), nullable=False),
            sa.Column("bottle_count", sa.Integer(), nullable=False),
            sa.Column("warnings", sa.JSON(), nullable=False),
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("status IN ('draft', 'confirmed', 'failed')", name="ck_import_batches_status"),
            sa.CheckConstraint("row_count >= 0", name="ck_import_batches_row_count_non_negative"),
            sa.CheckConstraint("valid_rows >= 0", name="ck_import_batches_valid_rows_non_negative"),
            sa.CheckConstraint("invalid_rows >= 0", name="ck_import_batches_invalid_rows_non_negative"),
            sa.CheckConstraint("bottle_count >= 0", name="ck_import_batches_bottle_count_non_negative"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("import_batches")

    if "import_batch_rows" not in existing_tables:
        op.create_table(
            "import_batch_rows",
            sa.Column("batch_id", sa.String(length=36), nullable=False),
            sa.Column("source_row_number", sa.Integer(), nullable=False),
            sa.Column("raw_row", sa.JSON(), nullable=False),
            sa.Column("normalized_row", sa.JSON(), nullable=True),
            sa.Column("row_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("errors", sa.JSON(), nullable=False),
            sa.Column("warnings", sa.JSON(), nullable=False),
            sa.Column("created_bottle_ids", sa.JSON(), nullable=False),
            sa.Column("created_transaction_ids", sa.JSON(), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("source_row_number > 0", name="ck_import_batch_rows_source_row_positive"),
            sa.CheckConstraint("status IN ('valid', 'invalid', 'imported')", name="ck_import_batch_rows_status"),
            sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("batch_id", "source_row_number", name="uq_import_batch_rows_batch_source_row"),
        )
        existing_tables.add("import_batch_rows")

    _create_indexes()


def downgrade() -> None:
    raise RuntimeError("Import batch audit migration is not safely reversible.")


def _create_indexes() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
        existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, columns, unique=False)

    create_index_once("import_batches", "ix_import_batches_file_sha256", ["file_sha256"])
    create_index_once("import_batch_rows", "ix_import_batch_rows_batch_id", ["batch_id"])
    create_index_once("import_batch_rows", "ix_import_batch_rows_row_hash", ["row_hash"])
