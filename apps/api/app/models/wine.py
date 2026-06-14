from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
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
    wine_identity_key: Mapped[str | None] = mapped_column(String(512), index=True)
    quality_status: Mapped[str] = mapped_column(String(30), default="unreviewed", nullable=False, index=True)
    merged_into_id: Mapped[str | None] = mapped_column(String(36), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    producer: Mapped["Producer"] = relationship("Producer", back_populates="wines")
    vintages: Mapped[list["Vintage"]] = relationship("Vintage", back_populates="wine")
