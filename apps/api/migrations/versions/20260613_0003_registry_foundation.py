"""Add registry foundation governance tables.

Revision ID: 20260613_0003
Revises: 20260613_0002
Create Date: 2026-06-13
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect, text

revision = "20260613_0003"
down_revision = "20260613_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_tables = set(inspect(bind).get_table_names())

    _add_registry_columns()
    _create_registry_tables(existing_tables)
    _create_indexes()
    _backfill_registry_keys()


def downgrade() -> None:
    raise RuntimeError("Registry foundation migration is not safely reversible.")


def _add_registry_columns() -> None:
    _add_column_once("producers", sa.Column("canonical_key", sa.String(length=255), nullable=True))
    _add_column_once(
        "producers",
        sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="unreviewed"),
    )
    _add_column_once("producers", sa.Column("merged_into_id", sa.String(length=36), nullable=True))
    _add_column_once("producers", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))

    _add_column_once("wines", sa.Column("wine_identity_key", sa.String(length=512), nullable=True))
    _add_column_once(
        "wines",
        sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="unreviewed"),
    )
    _add_column_once("wines", sa.Column("merged_into_id", sa.String(length=36), nullable=True))
    _add_column_once("wines", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))

    _add_column_once(
        "vintages",
        sa.Column("quality_status", sa.String(length=30), nullable=False, server_default="unreviewed"),
    )
    _add_column_once("vintages", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))


def _add_column_once(table_name: str, column: sa.Column) -> None:
    bind = op.get_bind()
    columns = {item["name"] for item in inspect(bind).get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def _create_registry_tables(existing_tables: set[str]) -> None:
    if "registry_aliases" not in existing_tables:
        op.create_table(
            "registry_aliases",
            sa.Column("entity_type", sa.String(length=30), nullable=False),
            sa.Column("entity_id", sa.String(length=36), nullable=False),
            sa.Column("alias_text", sa.Text(), nullable=False),
            sa.Column("alias_key", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("source", sa.String(length=120), nullable=True),
            sa.Column("rule_version", sa.String(length=40), nullable=False),
            sa.Column("confidence", sa.String(length=20), nullable=True),
            sa.Column("import_mapping_id", sa.String(length=36), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("entity_type IN ('producer', 'wine', 'vintage')", name="ck_registry_aliases_entity_type"),
            sa.CheckConstraint(
                "status IN ('observed', 'candidate', 'approved', 'rejected', 'conflict')",
                name="ck_registry_aliases_status",
            ),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("registry_aliases")

    if "import_mappings" not in existing_tables:
        op.create_table(
            "import_mappings",
            sa.Column("source", sa.String(length=120), nullable=False),
            sa.Column("import_batch_id", sa.String(length=36), nullable=True),
            sa.Column("import_batch_row_id", sa.String(length=36), nullable=True),
            sa.Column("source_row_number", sa.Integer(), nullable=True),
            sa.Column("raw_value", sa.JSON(), nullable=True),
            sa.Column("target_entity_type", sa.String(length=30), nullable=False),
            sa.Column("target_entity_id", sa.String(length=36), nullable=True),
            sa.Column("match_score", sa.Integer(), nullable=False),
            sa.Column("decision", sa.String(length=30), nullable=False),
            sa.Column("rule_version", sa.String(length=40), nullable=False),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "target_entity_type IN ('producer', 'wine', 'vintage')",
                name="ck_import_mappings_target_type",
            ),
            sa.CheckConstraint(
                "decision IN ('auto_accepted', 'needs_review', 'manual_required', 'rejected')",
                name="ck_import_mappings_decision",
            ),
            sa.CheckConstraint("match_score >= 0 AND match_score <= 100", name="ck_import_mappings_match_score"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("import_mappings")

    if "registry_review_queue" not in existing_tables:
        op.create_table(
            "registry_review_queue",
            sa.Column("review_type", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("source", sa.String(length=120), nullable=True),
            sa.Column("entity_type", sa.String(length=30), nullable=True),
            sa.Column("entity_id", sa.String(length=36), nullable=True),
            sa.Column("import_mapping_id", sa.String(length=36), nullable=True),
            sa.Column("raw_value", sa.JSON(), nullable=True),
            sa.Column("match_score", sa.Integer(), nullable=True),
            sa.Column("title", sa.Text(), nullable=False),
            sa.Column("detail", sa.Text(), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=True),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "review_type IN ('match_range', 'alias_conflict', 'suspected_duplicate', 'missing_field')",
                name="ck_registry_review_queue_type",
            ),
            sa.CheckConstraint("status IN ('open', 'closed')", name="ck_registry_review_queue_status"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("registry_review_queue")

    if "registry_quality_findings" not in existing_tables:
        op.create_table(
            "registry_quality_findings",
            sa.Column("finding_type", sa.String(length=50), nullable=False),
            sa.Column("severity", sa.String(length=20), nullable=False),
            sa.Column("entity_type", sa.String(length=30), nullable=True),
            sa.Column("entity_id", sa.String(length=36), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=False),
            sa.Column("evidence_hash", sa.String(length=64), nullable=False),
            sa.Column("suggested_action", sa.Text(), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "finding_type IN ("
                "'duplicate_producer', 'duplicate_wine', 'alias_conflict', 'missing_vintage', "
                "'missing_drink_window', 'missing_region', 'missing_country'"
                ")",
                name="ck_registry_quality_findings_type",
            ),
            sa.CheckConstraint(
                "severity IN ('low', 'medium', 'high')",
                name="ck_registry_quality_findings_severity",
            ),
            sa.CheckConstraint("status IN ('open', 'closed')", name="ck_registry_quality_findings_status"),
            sa.PrimaryKeyConstraint("id"),
        )
        existing_tables.add("registry_quality_findings")


def _create_indexes() -> None:
    _create_index_once("producers", "ix_producers_canonical_key", ["canonical_key"])
    _create_index_once("producers", "ix_producers_quality_status", ["quality_status"])
    _create_index_once("producers", "ix_producers_merged_into_id", ["merged_into_id"])
    _create_index_once("wines", "ix_wines_wine_identity_key", ["wine_identity_key"])
    _create_index_once("wines", "ix_wines_quality_status", ["quality_status"])
    _create_index_once("wines", "ix_wines_merged_into_id", ["merged_into_id"])
    _create_index_once("vintages", "ix_vintages_quality_status", ["quality_status"])

    for table_name, columns in {
        "registry_aliases": [
            ("ix_registry_aliases_entity_type", ["entity_type"]),
            ("ix_registry_aliases_entity_id", ["entity_id"]),
            ("ix_registry_aliases_alias_key", ["alias_key"]),
            ("ix_registry_aliases_status", ["status"]),
            ("ix_registry_aliases_import_mapping_id", ["import_mapping_id"]),
        ],
        "import_mappings": [
            ("ix_import_mappings_source", ["source"]),
            ("ix_import_mappings_import_batch_id", ["import_batch_id"]),
            ("ix_import_mappings_import_batch_row_id", ["import_batch_row_id"]),
            ("ix_import_mappings_target_entity_type", ["target_entity_type"]),
            ("ix_import_mappings_target_entity_id", ["target_entity_id"]),
            ("ix_import_mappings_decision", ["decision"]),
        ],
        "registry_review_queue": [
            ("ix_registry_review_queue_review_type", ["review_type"]),
            ("ix_registry_review_queue_status", ["status"]),
            ("ix_registry_review_queue_source", ["source"]),
            ("ix_registry_review_queue_entity_type", ["entity_type"]),
            ("ix_registry_review_queue_entity_id", ["entity_id"]),
            ("ix_registry_review_queue_import_mapping_id", ["import_mapping_id"]),
        ],
        "registry_quality_findings": [
            ("ix_registry_quality_findings_finding_type", ["finding_type"]),
            ("ix_registry_quality_findings_severity", ["severity"]),
            ("ix_registry_quality_findings_entity_type", ["entity_type"]),
            ("ix_registry_quality_findings_entity_id", ["entity_id"]),
            ("ix_registry_quality_findings_evidence_hash", ["evidence_hash"]),
            ("ix_registry_quality_findings_status", ["status"]),
        ],
    }.items():
        for index_name, index_columns in columns:
            _create_index_once(table_name, index_name, index_columns)


def _create_index_once(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in set(inspector.get_table_names()):
        return
    existing_indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name not in existing_indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def _backfill_registry_keys() -> None:
    bind = op.get_bind()
    producers = bind.execute(text("SELECT id, name_original, name_cn FROM producers")).mappings().all()
    for producer in producers:
        bind.execute(
            text("UPDATE producers SET canonical_key = :canonical_key WHERE id = :id AND canonical_key IS NULL"),
            {
                "id": producer["id"],
                "canonical_key": _producer_key(producer["name_original"], producer["name_cn"]),
            },
        )

    wines = bind.execute(
        text(
            """
            SELECT
                w.id,
                w.name_original,
                w.country,
                w.region,
                w.appellation,
                w.type,
                p.canonical_key AS producer_key,
                p.name_original AS producer_name
            FROM wines w
            JOIN producers p ON p.id = w.producer_id
            """
        )
    ).mappings().all()
    for wine in wines:
        bind.execute(
            text("UPDATE wines SET wine_identity_key = :wine_identity_key WHERE id = :id AND wine_identity_key IS NULL"),
            {
                "id": wine["id"],
                "wine_identity_key": _wine_identity_key(
                    wine["producer_key"] or _producer_key(wine["producer_name"], None),
                    wine["name_original"],
                    wine["country"],
                    wine["region"],
                    wine["appellation"],
                    wine["type"],
                ),
            },
        )


def _producer_key(name_original: str | None, name_cn: str | None) -> str:
    return _normalize_registry_text(name_original or name_cn or "unknown producer")


def _wine_identity_key(
    producer_key: str | None,
    wine_name: str | None,
    country: str | None,
    region: str | None,
    appellation: str | None,
    wine_type: str | None,
) -> str:
    producer_part = producer_key or "unknown producer"
    parts = [
        producer_part,
        _normalize_registry_text(wine_name or "unknown wine"),
        _normalize_registry_text(country or ""),
        _normalize_registry_text(region or ""),
        _normalize_registry_text(appellation or ""),
        _normalize_registry_text(wine_type or ""),
    ]
    return " | ".join(part for part in parts if part)


_PUNCT_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "`": "'",
        "´": "'",
        "“": '"',
        "”": '"',
        "‐": "-",
        "‑": "-",
        "–": "-",
        "—": "-",
        "－": "-",
        "·": " ",
        "•": " ",
        "，": ",",
        "。": ".",
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
    }
)


def _normalize_registry_text(value: str) -> str:
    text_value = unicodedata.normalize("NFKC", value).translate(_PUNCT_TRANSLATION).strip().casefold()
    text_value = "".join(
        ch for ch in unicodedata.normalize("NFKD", text_value) if not unicodedata.combining(ch)
    )
    text_value = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", text_value)
    return re.sub(r"\s+", " ", text_value).strip()


def _evidence_hash(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
