from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Producer(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "producers"

    name_original: Mapped[str] = mapped_column(Text, nullable=False)
    name_cn: Mapped[str | None] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(150))
    website: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list[str] | dict[str, Any] | None] = mapped_column(JSON)
    canonical_key: Mapped[str | None] = mapped_column(String(255), index=True)
    quality_status: Mapped[str] = mapped_column(String(30), default="unreviewed", nullable=False, index=True)
    merged_into_id: Mapped[str | None] = mapped_column(String(36), index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    wines: Mapped[list["Wine"]] = relationship("Wine", back_populates="producer")
