from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class DrinkWindow(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "drink_windows"
    __table_args__ = (
        CheckConstraint("drink_from IS NULL OR drink_to IS NULL OR drink_from <= drink_to", name="ck_drink_windows_order"),
        CheckConstraint("peak_from IS NULL OR peak_to IS NULL OR peak_from <= peak_to", name="ck_drink_windows_peak_order"),
        CheckConstraint("confidence IN ('low', 'medium', 'high')", name="ck_drink_windows_confidence"),
    )

    vintage_id: Mapped[str] = mapped_column(ForeignKey("vintages.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_detail: Mapped[str | None] = mapped_column(Text)
    drink_from: Mapped[int | None] = mapped_column(Integer)
    drink_to: Mapped[int | None] = mapped_column(Integer)
    peak_from: Mapped[int | None] = mapped_column(Integer)
    peak_to: Mapped[int | None] = mapped_column(Integer)
    confidence: Mapped[str] = mapped_column(String(20), default="low", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    vintage: Mapped["Vintage"] = relationship("Vintage", back_populates="drink_windows")
