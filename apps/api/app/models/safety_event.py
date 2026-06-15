from __future__ import annotations

from typing import Any

from sqlalchemy import CheckConstraint, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, CreatedAtMixin, UuidPrimaryKeyMixin


class SafetyEvent(UuidPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "safety_events"
    __table_args__ = (
        CheckConstraint(
            "event_type IN ('BACKUP_CREATED', 'RESTORE_COMPLETED')",
            name="ck_safety_events_type",
        ),
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    artifact_name: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_path: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    reason: Mapped[str | None] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String(120))
    event_metadata: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSON)
