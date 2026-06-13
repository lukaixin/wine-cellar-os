"""Initial Alpha schema baseline.

Revision ID: 20260613_0001
Revises:
Create Date: 2026-06-13
"""

from __future__ import annotations

from collections.abc import Callable

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "20260613_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    def create_table_once(table_name: str, create: Callable[[], None]) -> None:
        if table_name not in existing_tables:
            create()
            existing_tables.add(table_name)

    create_table_once(
        "producers",
        lambda: op.create_table(
            "producers",
            sa.Column("name_original", sa.Text(), nullable=False),
            sa.Column("name_cn", sa.Text(), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column("region", sa.String(length=150), nullable=True),
            sa.Column("website", sa.Text(), nullable=True),
            sa.Column("aliases", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "cellars",
        lambda: op.create_table(
            "cellars",
            sa.Column("name", sa.Text(), nullable=False),
            sa.Column("cellar_type", sa.String(length=50), nullable=False),
            sa.Column("rows", sa.Integer(), nullable=True),
            sa.Column("columns", sa.Integer(), nullable=True),
            sa.Column("temperature_target", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("humidity_target", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "media_assets",
        lambda: op.create_table(
            "media_assets",
            sa.Column("owner_type", sa.String(length=40), nullable=False),
            sa.Column("owner_id", sa.String(length=36), nullable=False),
            sa.Column("media_type", sa.String(length=80), nullable=False),
            sa.Column("file_path", sa.Text(), nullable=False),
            sa.Column("file_hash", sa.String(length=128), nullable=True),
            sa.Column("mime_type", sa.String(length=120), nullable=True),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("owner_type IN ('bottle', 'wine', 'vintage', 'transaction')", name="ck_media_assets_owner_type"),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "tags",
        lambda: op.create_table(
            "tags",
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name"),
        ),
    )
    create_table_once(
        "wines",
        lambda: op.create_table(
            "wines",
            sa.Column("producer_id", sa.String(length=36), nullable=False),
            sa.Column("name_original", sa.Text(), nullable=False),
            sa.Column("name_cn", sa.Text(), nullable=True),
            sa.Column("type", sa.String(length=50), nullable=True),
            sa.Column("color", sa.String(length=50), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column("region", sa.String(length=150), nullable=True),
            sa.Column("appellation", sa.String(length=150), nullable=True),
            sa.Column("grape_varieties", sa.JSON(), nullable=True),
            sa.Column("classification", sa.String(length=150), nullable=True),
            sa.Column("lwin7", sa.String(length=20), nullable=True),
            sa.Column("aliases", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["producer_id"], ["producers.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "locations",
        lambda: op.create_table(
            "locations",
            sa.Column("cellar_id", sa.String(length=36), nullable=False),
            sa.Column("code", sa.String(length=80), nullable=False),
            sa.Column("row_index", sa.Integer(), nullable=True),
            sa.Column("column_index", sa.Integer(), nullable=True),
            sa.Column("layer_index", sa.Integer(), nullable=True),
            sa.Column("position_note", sa.Text(), nullable=True),
            sa.Column("capacity", sa.Integer(), nullable=False),
            sa.Column("location_type", sa.String(length=50), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("capacity >= 0", name="ck_locations_capacity_non_negative"),
            sa.ForeignKeyConstraint(["cellar_id"], ["cellars.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("cellar_id", "code", name="uq_locations_cellar_code"),
        ),
    )
    create_table_once(
        "vintages",
        lambda: op.create_table(
            "vintages",
            sa.Column("wine_id", sa.String(length=36), nullable=False),
            sa.Column("vintage_year", sa.Integer(), nullable=True),
            sa.Column("is_non_vintage", sa.Boolean(), nullable=False),
            sa.Column("lwin11", sa.String(length=20), nullable=True),
            sa.Column("critic_score", sa.Numeric(precision=5, scale=2), nullable=True),
            sa.Column("critic_source", sa.String(length=150), nullable=True),
            sa.Column("default_drink_from", sa.Integer(), nullable=True),
            sa.Column("default_drink_to", sa.Integer(), nullable=True),
            sa.Column("drink_window_confidence", sa.String(length=20), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "default_drink_from IS NULL OR default_drink_to IS NULL OR default_drink_from <= default_drink_to",
                name="ck_vintages_default_drink_window_order",
            ),
            sa.CheckConstraint(
                "drink_window_confidence IS NULL OR drink_window_confidence IN ('low', 'medium', 'high')",
                name="ck_vintages_drink_window_confidence",
            ),
            sa.ForeignKeyConstraint(["wine_id"], ["wines.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("wine_id", "vintage_year", "is_non_vintage", name="uq_vintages_wine_year_nv"),
        ),
    )
    create_table_once(
        "object_tags",
        lambda: op.create_table(
            "object_tags",
            sa.Column("tag_id", sa.String(length=36), nullable=False),
            sa.Column("owner_type", sa.String(length=40), nullable=False),
            sa.Column("owner_id", sa.String(length=36), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("owner_type IN ('wine', 'vintage', 'bottle')", name="ck_object_tags_owner_type"),
            sa.ForeignKeyConstraint(["tag_id"], ["tags.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("tag_id", "owner_type", "owner_id", name="uq_object_tags_tag_owner"),
        ),
    )
    create_table_once(
        "bottles",
        lambda: op.create_table(
            "bottles",
            sa.Column("vintage_id", sa.String(length=36), nullable=False),
            sa.Column("bottle_size_ml", sa.Integer(), nullable=False),
            sa.Column("lwin16", sa.String(length=30), nullable=True),
            sa.Column("acquisition_date", sa.Date(), nullable=True),
            sa.Column("purchase_price", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("purchase_currency", sa.String(length=10), nullable=False),
            sa.Column("purchase_source", sa.Text(), nullable=True),
            sa.Column("purchase_channel", sa.Text(), nullable=True),
            sa.Column("condition", sa.String(length=80), nullable=True),
            sa.Column("current_status", sa.String(length=30), nullable=False),
            sa.Column("current_location_id", sa.String(length=36), nullable=True),
            sa.Column("personal_rating", sa.Integer(), nullable=True),
            sa.Column("personal_notes", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("bottle_size_ml > 0", name="ck_bottles_size_positive"),
            sa.CheckConstraint(
                "current_status IN ('in_stock', 'drunk', 'gifted', 'sold', 'damaged', 'lost', 'returned')",
                name="ck_bottles_current_status",
            ),
            sa.ForeignKeyConstraint(["current_location_id"], ["locations.id"]),
            sa.ForeignKeyConstraint(["vintage_id"], ["vintages.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "drink_windows",
        lambda: op.create_table(
            "drink_windows",
            sa.Column("vintage_id", sa.String(length=36), nullable=False),
            sa.Column("source", sa.String(length=120), nullable=False),
            sa.Column("source_detail", sa.Text(), nullable=True),
            sa.Column("drink_from", sa.Integer(), nullable=True),
            sa.Column("drink_to", sa.Integer(), nullable=True),
            sa.Column("peak_from", sa.Integer(), nullable=True),
            sa.Column("peak_to", sa.Integer(), nullable=True),
            sa.Column("confidence", sa.String(length=20), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("drink_from IS NULL OR drink_to IS NULL OR drink_from <= drink_to", name="ck_drink_windows_order"),
            sa.CheckConstraint("peak_from IS NULL OR peak_to IS NULL OR peak_from <= peak_to", name="ck_drink_windows_peak_order"),
            sa.CheckConstraint("confidence IN ('low', 'medium', 'high')", name="ck_drink_windows_confidence"),
            sa.ForeignKeyConstraint(["vintage_id"], ["vintages.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "valuation_snapshots",
        lambda: op.create_table(
            "valuation_snapshots",
            sa.Column("vintage_id", sa.String(length=36), nullable=False),
            sa.Column("bottle_size_ml", sa.Integer(), nullable=False),
            sa.Column("source", sa.String(length=120), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("region", sa.String(length=120), nullable=True),
            sa.Column("currency", sa.String(length=10), nullable=False),
            sa.Column("low_price", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("avg_price", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("median_price", sa.Numeric(precision=12, scale=2), nullable=True),
            sa.Column("tax_included", sa.Boolean(), nullable=True),
            sa.Column("shipping_included", sa.Boolean(), nullable=True),
            sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("confidence", sa.String(length=20), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("bottle_size_ml > 0", name="ck_valuation_snapshots_size_positive"),
            sa.CheckConstraint("confidence IN ('low', 'medium', 'high')", name="ck_valuation_snapshots_confidence"),
            sa.ForeignKeyConstraint(["vintage_id"], ["vintages.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "inventory_transactions",
        lambda: op.create_table(
            "inventory_transactions",
            sa.Column("bottle_id", sa.String(length=36), nullable=False),
            sa.Column("transaction_type", sa.String(length=50), nullable=False),
            sa.Column("from_location_id", sa.String(length=36), nullable=True),
            sa.Column("to_location_id", sa.String(length=36), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("actor", sa.String(length=120), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "\n            transaction_type NOT IN ('IN')\n            OR to_location_id IS NOT NULL\n            ",
                name="ck_inventory_transactions_inbound_to_location",
            ),
            sa.CheckConstraint(
                "\n            transaction_type NOT IN ('CONSUME', 'GIFT', 'DAMAGE')\n            OR from_location_id IS NOT NULL\n            ",
                name="ck_inventory_transactions_outbound_from_location",
            ),
            sa.CheckConstraint(
                "transaction_type != 'MOVE' OR (from_location_id IS NOT NULL AND to_location_id IS NOT NULL)",
                name="ck_inventory_transactions_transfer_locations",
            ),
            sa.CheckConstraint(
                "transaction_type != 'ADJUST' OR (from_location_id IS NOT NULL OR to_location_id IS NOT NULL)",
                name="ck_inventory_transactions_adjust_location",
            ),
            sa.CheckConstraint(
                "transaction_type IN ('IN', 'MOVE', 'CONSUME', 'GIFT', 'DAMAGE', 'ADJUST')",
                name="ck_inventory_transactions_type",
            ),
            sa.ForeignKeyConstraint(["bottle_id"], ["bottles.id"]),
            sa.ForeignKeyConstraint(["from_location_id"], ["locations.id"]),
            sa.ForeignKeyConstraint(["to_location_id"], ["locations.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )
    create_table_once(
        "label_image_uploads",
        lambda: op.create_table(
            "label_image_uploads",
            sa.Column("original_filename", sa.Text(), nullable=False),
            sa.Column("stored_filename", sa.Text(), nullable=False),
            sa.Column("content_type", sa.String(length=120), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("sha256", sa.String(length=64), nullable=False),
            sa.Column("file_path", sa.Text(), nullable=False),
            sa.Column("bottle_id", sa.String(length=36), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["bottle_id"], ["bottles.id"]),
            sa.PrimaryKeyConstraint("id"),
        ),
    )

    _create_indexes()


def downgrade() -> None:
    raise RuntimeError("Initial Alpha baseline migration is not safely reversible.")


def _create_indexes() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    def create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
        existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name not in existing_indexes:
            op.create_index(index_name, table_name, columns, unique=False)

    create_index_once("bottles", "ix_bottles_current_location_id", ["current_location_id"])
    create_index_once("bottles", "ix_bottles_lwin16", ["lwin16"])
    create_index_once("bottles", "ix_bottles_vintage_id", ["vintage_id"])
    create_index_once("drink_windows", "ix_drink_windows_vintage_id", ["vintage_id"])
    create_index_once("inventory_transactions", "ix_inventory_transactions_bottle_id", ["bottle_id"])
    create_index_once("inventory_transactions", "ix_inventory_transactions_from_location_id", ["from_location_id"])
    create_index_once("inventory_transactions", "ix_inventory_transactions_to_location_id", ["to_location_id"])
    create_index_once("label_image_uploads", "ix_label_image_uploads_bottle_id", ["bottle_id"])
    create_index_once("label_image_uploads", "ix_label_image_uploads_sha256", ["sha256"])
    create_index_once("locations", "ix_locations_cellar_id", ["cellar_id"])
    create_index_once("media_assets", "ix_media_assets_owner_id", ["owner_id"])
    create_index_once("object_tags", "ix_object_tags_owner_id", ["owner_id"])
    create_index_once("object_tags", "ix_object_tags_tag_id", ["tag_id"])
    create_index_once("valuation_snapshots", "ix_valuation_snapshots_vintage_id", ["vintage_id"])
    create_index_once("vintages", "ix_vintages_lwin11", ["lwin11"])
    create_index_once("vintages", "ix_vintages_wine_id", ["wine_id"])
    create_index_once("wines", "ix_wines_lwin7", ["lwin7"])
    create_index_once("wines", "ix_wines_producer_id", ["producer_id"])
