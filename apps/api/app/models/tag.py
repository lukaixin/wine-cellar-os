from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin


class Tag(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(80))

    object_tags: Mapped[list["ObjectTag"]] = relationship("ObjectTag", back_populates="tag")


class ObjectTag(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "object_tags"
    __table_args__ = (
        UniqueConstraint("tag_id", "owner_type", "owner_id", name="uq_object_tags_tag_owner"),
        CheckConstraint("owner_type IN ('wine', 'vintage', 'bottle')", name="ck_object_tags_owner_type"),
    )

    tag_id: Mapped[str] = mapped_column(ForeignKey("tags.id"), nullable=False, index=True)
    owner_type: Mapped[str] = mapped_column(String(40), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    tag: Mapped["Tag"] = relationship("Tag", back_populates="object_tags")
