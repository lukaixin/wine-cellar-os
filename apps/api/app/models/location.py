from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Location(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("cellar_id", "code", name="uq_locations_cellar_code"),
        CheckConstraint("capacity >= 0", name="ck_locations_capacity_non_negative"),
    )

    cellar_id: Mapped[str] = mapped_column(ForeignKey("cellars.id"), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    row_index: Mapped[int | None] = mapped_column(Integer)
    column_index: Mapped[int | None] = mapped_column(Integer)
    layer_index: Mapped[int | None] = mapped_column(Integer)
    position_note: Mapped[str | None] = mapped_column(Text)
    capacity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    location_type: Mapped[str] = mapped_column(String(50), default="grid", nullable=False)

    cellar: Mapped["Cellar"] = relationship("Cellar", back_populates="locations")
    bottles: Mapped[list["Bottle"]] = relationship(
        "Bottle",
        back_populates="current_location",
        foreign_keys="Bottle.current_location_id",
    )
    transactions_from: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction",
        back_populates="from_location",
        foreign_keys="InventoryTransaction.from_location_id",
    )
    transactions_to: Mapped[list["InventoryTransaction"]] = relationship(
        "InventoryTransaction",
        back_populates="to_location",
        foreign_keys="InventoryTransaction.to_location_id",
    )
