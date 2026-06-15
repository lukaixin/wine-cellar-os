from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin


class ImportBatch(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'confirmed', 'failed')", name="ck_import_batches_status"),
        CheckConstraint("row_count >= 0", name="ck_import_batches_row_count_non_negative"),
        CheckConstraint("valid_rows >= 0", name="ck_import_batches_valid_rows_non_negative"),
        CheckConstraint("invalid_rows >= 0", name="ck_import_batches_invalid_rows_non_negative"),
        CheckConstraint("bottle_count >= 0", name="ck_import_batches_bottle_count_non_negative"),
    )

    source_filename: Mapped[str] = mapped_column(Text, nullable=False)
    sheet_name: Mapped[str] = mapped_column(String(120), nullable=False)
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    valid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    invalid_rows: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bottle_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warnings: Mapped[list[str] | dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    compensated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    compensation_reason: Mapped[str | None] = mapped_column(Text)
    compensation_transaction_ids: Mapped[list[str] | dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)

    rows: Mapped[list["ImportBatchRow"]] = relationship("ImportBatchRow", back_populates="batch")


class ImportBatchRow(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "import_batch_rows"
    __table_args__ = (
        UniqueConstraint("batch_id", "source_row_number", name="uq_import_batch_rows_batch_source_row"),
        CheckConstraint("source_row_number > 0", name="ck_import_batch_rows_source_row_positive"),
        CheckConstraint("status IN ('valid', 'invalid', 'imported')", name="ck_import_batch_rows_status"),
    )

    batch_id: Mapped[str] = mapped_column(ForeignKey("import_batches.id"), nullable=False, index=True)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_row: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    normalized_row: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    row_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    errors: Mapped[list[str] | dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    warnings: Mapped[list[str] | dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    created_bottle_ids: Mapped[list[str] | dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)
    created_transaction_ids: Mapped[list[str] | dict[str, Any]] = mapped_column(JSON, default=list, nullable=False)

    batch: Mapped["ImportBatch"] = relationship("ImportBatch", back_populates="rows")
