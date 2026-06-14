from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Bottle(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bottles"
    __table_args__ = (
        CheckConstraint("bottle_size_ml > 0", name="ck_bottles_size_positive"),
        CheckConstraint(
            "current_status IN ('in_stock', 'drunk', 'gifted', 'sold', 'damaged', 'lost', 'returned')",
            name="ck_bottles_current_status",
        ),
    )

    vintage_id: Mapped[str] = mapped_column(ForeignKey("vintages.id"), nullable=False, index=True)
    bottle_size_ml: Mapped[int] = mapped_column(Integer, default=750, nullable=False)
    lwin16: Mapped[str | None] = mapped_column(String(30), index=True)
    acquisition_date: Mapped[date | None] = mapped_column(Date)
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    purchase_currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    purchase_source: Mapped[str | None] = mapped_column(Text)
    purchase_channel: Mapped[str | None] = mapped_column(Text)
    ws_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    condition: Mapped[str | None] = mapped_column(String(80))
    current_status: Mapped[str] = mapped_column(String(30), nullable=False)
    current_location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id"), index=True)
    personal_rating: Mapped[int | None] = mapped_column(Integer)
    personal_notes: Mapped[str | None] = mapped_column(Text)

    vintage: Mapped["Vintage"] = relationship("Vintage", back_populates="bottles")
    current_location: Mapped["Location | None"] = relationship(
        "Location",
        back_populates="bottles",
        foreign_keys=[current_location_id],
    )
    transactions: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction",
        back_populates="bottle",
        foreign_keys="InventoryTransaction.bottle_id",
    )
