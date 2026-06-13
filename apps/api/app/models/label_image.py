from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin


class LabelImageUpload(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "label_image_uploads"

    original_filename: Mapped[str] = mapped_column(Text, nullable=False)
    stored_filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    bottle_id: Mapped[str | None] = mapped_column(ForeignKey("bottles.id"), index=True)

    bottle: Mapped["Bottle | None"] = relationship("Bottle", foreign_keys=[bottle_id])
