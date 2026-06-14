"""Add nullable Wine-Searcher price to bottles.

Revision ID: 20260614_0004
Revises: 20260613_0003
Create Date: 2026-06-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20260614_0004"
down_revision = "20260613_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in inspect(bind).get_columns("bottles")}
    if "ws_price" not in columns:
        op.add_column("bottles", sa.Column("ws_price", sa.Numeric(12, 2), nullable=True))


def downgrade() -> None:
    raise RuntimeError("Bottle WS Price migration is not safely reversible.")
