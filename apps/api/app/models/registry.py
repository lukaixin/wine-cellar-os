from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, TimestampMixin, UuidPrimaryKeyMixin


class RegistryAlias(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "registry_aliases"
    __table_args__ = (
        CheckConstraint("entity_type IN ('producer', 'wine', 'vintage')", name="ck_registry_aliases_entity_type"),
        CheckConstraint(
            "status IN ('observed', 'candidate', 'approved', 'rejected', 'conflict')",
            name="ck_registry_aliases_status",
        ),
    )

    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    alias_text: Mapped[str] = mapped_column(Text, nullable=False)
    alias_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="observed", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(120))
    rule_version: Mapped[str] = mapped_column(String(40), default="registry-v1", nullable=False)
    confidence: Mapped[str | None] = mapped_column(String(20))
    import_mapping_id: Mapped[str | None] = mapped_column(String(36), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)


class ImportMapping(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "import_mappings"
    __table_args__ = (
        CheckConstraint("target_entity_type IN ('producer', 'wine', 'vintage')", name="ck_import_mappings_target_type"),
        CheckConstraint(
            "decision IN ('auto_accepted', 'needs_review', 'manual_required', 'rejected')",
            name="ck_import_mappings_decision",
        ),
        CheckConstraint("match_score >= 0 AND match_score <= 100", name="ck_import_mappings_match_score"),
    )

    source: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    import_batch_id: Mapped[str | None] = mapped_column(String(36), index=True)
    import_batch_row_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_row_number: Mapped[int | None] = mapped_column(Integer)
    raw_value: Mapped[dict[str, Any] | str | None] = mapped_column(JSON)
    target_entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    target_entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    rule_version: Mapped[str] = mapped_column(String(40), default="registry-v1", nullable=False)
    evidence: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)


class RegistryReviewQueue(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "registry_review_queue"
    __table_args__ = (
        CheckConstraint(
            "review_type IN ('match_range', 'alias_conflict', 'suspected_duplicate', 'missing_field')",
            name="ck_registry_review_queue_type",
        ),
        CheckConstraint("status IN ('open', 'closed')", name="ck_registry_review_queue_status"),
    )

    review_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
    source: Mapped[str | None] = mapped_column(String(120), index=True)
    entity_type: Mapped[str | None] = mapped_column(String(30), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    import_mapping_id: Mapped[str | None] = mapped_column(String(36), index=True)
    raw_value: Mapped[dict[str, Any] | str | None] = mapped_column(JSON)
    match_score: Mapped[int | None] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)


class RegistryQualityFinding(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "registry_quality_findings"
    __table_args__ = (
        CheckConstraint(
            "finding_type IN ("
            "'duplicate_producer', 'duplicate_wine', 'alias_conflict', 'missing_vintage', "
            "'missing_drink_window', 'missing_region', 'missing_country'"
            ")",
            name="ck_registry_quality_findings_type",
        ),
        CheckConstraint("severity IN ('low', 'medium', 'high')", name="ck_registry_quality_findings_severity"),
        CheckConstraint("status IN ('open', 'closed')", name="ck_registry_quality_findings_status"),
    )

    finding_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(30), index=True)
    entity_id: Mapped[str | None] = mapped_column(String(36), index=True)
    evidence: Mapped[dict[str, Any] | list[Any]] = mapped_column(JSON, nullable=False)
    evidence_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    suggested_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False, index=True)
