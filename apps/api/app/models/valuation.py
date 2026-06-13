from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin, utcnow


class ValuationSnapshot(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "valuation_snapshots"
    __table_args__ = (
        CheckConstraint("bottle_size_ml > 0", name="ck_valuation_snapshots_size_positive"),
        CheckConstraint("confidence IN ('low', 'medium', 'high')", name="ck_valuation_snapshots_confidence"),
    )

    vintage_id: Mapped[str] = mapped_column(ForeignKey("vintages.id"), nullable=False, index=True)
    bottle_size_ml: Mapped[int] = mapped_column(Integer, default=750, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    low_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    avg_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    median_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    tax_included: Mapped[bool | None] = mapped_column(Boolean)
    shipping_included: Mapped[bool | None] = mapped_column(Boolean)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    vintage: Mapped["Vintage"] = relationship("Vintage", back_populates="valuation_snapshots")
