from __future__ import annotations

from typing import Any

from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Wine(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "wines"

    producer_id: Mapped[str] = mapped_column(ForeignKey("producers.id"), nullable=False, index=True)
    name_original: Mapped[str] = mapped_column(Text, nullable=False)
    name_cn: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str | None] = mapped_column(String(50))
    color: Mapped[str | None] = mapped_column(String(50))
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(150))
    appellation: Mapped[str | None] = mapped_column(String(150))
    grape_varieties: Mapped[list[str] | dict[str, Any] | None] = mapped_column(JSON)
    classification: Mapped[str | None] = mapped_column(String(150))
    lwin7: Mapped[str | None] = mapped_column(String(20), index=True)
    aliases: Mapped[list[str] | dict[str, Any] | None] = mapped_column(JSON)

    producer: Mapped["Producer"] = relationship("Producer", back_populates="wines")
    vintages: Mapped[list["Vintage"]] = relationship("Vintage", back_populates="wine")
