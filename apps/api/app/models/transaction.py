from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin, utcnow


class InventoryTransaction(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "inventory_transactions"
    __table_args__ = (
        CheckConstraint(
            """
            transaction_type NOT IN ('IN')
            OR to_location_id IS NOT NULL
            """,
            name="ck_inventory_transactions_inbound_to_location",
        ),
        CheckConstraint(
            """
            transaction_type NOT IN ('CONSUME', 'GIFT', 'DAMAGE')
            OR from_location_id IS NOT NULL
            """,
            name="ck_inventory_transactions_outbound_from_location",
        ),
        CheckConstraint(
            "transaction_type != 'MOVE' OR (from_location_id IS NOT NULL AND to_location_id IS NOT NULL)",
            name="ck_inventory_transactions_transfer_locations",
        ),
        CheckConstraint(
            "transaction_type != 'ADJUST' OR (from_location_id IS NOT NULL OR to_location_id IS NOT NULL)",
            name="ck_inventory_transactions_adjust_location",
        ),
        CheckConstraint(
            "transaction_type IN ('IN', 'MOVE', 'CONSUME', 'GIFT', 'DAMAGE', 'ADJUST')",
            name="ck_inventory_transactions_type",
        ),
    )

    bottle_id: Mapped[str] = mapped_column(ForeignKey("bottles.id"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    from_location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id"), index=True)
    to_location_id: Mapped[str | None] = mapped_column(ForeignKey("locations.id"), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    actor: Mapped[str | None] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

    bottle: Mapped["Bottle"] = relationship(
        "Bottle",
        back_populates="transactions",
        foreign_keys=[bottle_id],
    )
    from_location: Mapped["Location | None"] = relationship(
        "Location",
        back_populates="transactions_from",
        foreign_keys=[from_location_id],
    )
    to_location: Mapped["Location | None"] = relationship(
        "Location",
        back_populates="transactions_to",
        foreign_keys=[to_location_id],
    )
