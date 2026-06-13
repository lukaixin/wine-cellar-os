from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Vintage(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "vintages"
    __table_args__ = (
        UniqueConstraint("wine_id", "vintage_year", "is_non_vintage", name="uq_vintages_wine_year_nv"),
        CheckConstraint(
            "default_drink_from IS NULL OR default_drink_to IS NULL OR default_drink_from <= default_drink_to",
            name="ck_vintages_default_drink_window_order",
        ),
        CheckConstraint(
            "drink_window_confidence IS NULL OR drink_window_confidence IN ('low', 'medium', 'high')",
            name="ck_vintages_drink_window_confidence",
        ),
    )

    wine_id: Mapped[str] = mapped_column(ForeignKey("wines.id"), nullable=False, index=True)
    vintage_year: Mapped[int | None] = mapped_column(Integer)
    is_non_vintage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    lwin11: Mapped[str | None] = mapped_column(String(20), index=True)
    critic_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    critic_source: Mapped[str | None] = mapped_column(String(150))
    default_drink_from: Mapped[int | None] = mapped_column(Integer)
    default_drink_to: Mapped[int | None] = mapped_column(Integer)
    drink_window_confidence: Mapped[str | None] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)

    wine: Mapped["Wine"] = relationship("Wine", back_populates="vintages")
    bottles: Mapped[list["Bottle"]] = relationship("Bottle", back_populates="vintage")
    drink_windows: Mapped[list["DrinkWindow"]] = relationship("DrinkWindow", back_populates="vintage")
    valuation_snapshots: Mapped[list["ValuationSnapshot"]] = relationship(
        "ValuationSnapshot",
        back_populates="vintage",
    )
