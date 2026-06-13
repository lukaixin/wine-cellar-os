from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UuidPrimaryKeyMixin


class Cellar(UuidPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cellars"

    name: Mapped[str] = mapped_column(Text, nullable=False)
    cellar_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rows: Mapped[int | None] = mapped_column(Integer)
    columns: Mapped[int | None] = mapped_column(Integer)
    temperature_target: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    humidity_target: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    notes: Mapped[str | None] = mapped_column(Text)

    locations: Mapped[list["Location"]] = relationship("Location", back_populates="cellar")
