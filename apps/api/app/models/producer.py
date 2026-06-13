from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String, Text
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

    wines: Mapped[list["Wine"]] = relationship("Wine", back_populates="producer")
