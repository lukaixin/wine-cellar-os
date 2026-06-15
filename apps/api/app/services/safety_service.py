from __future__ import annotations

import hashlib
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.core.database import create_app_engine, engine as app_engine
from app.models import SafetyEvent
from app.models.base import utcnow

CURRENT_ALEMBIC_VERSION = "20260614_0005"


@dataclass(frozen=True)
class BackupTarget:
    database_path: Path
    backup_dir: Path


def sqlite_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.drivername not in {"sqlite", "sqlite+pysqlite"} or not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


class SafetyService:
    def __init__(self, database_url: str | None = None, backup_dir: str | None = None) -> None:
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        database_path = sqlite_path(self.database_url)
        if database_path is None:
            raise HTTPException(status_code=422, detail="Safety operations require a file-based SQLite database.")
        self.target = BackupTarget(
            database_path=database_path,
            backup_dir=(Path(backup_dir).expanduser().resolve() if backup_dir else database_path.parent / "backups"),
        )

    def list_backups(self) -> dict[str, Any]:
        self.target.backup_dir.mkdir(parents=True, exist_ok=True)
        backups = []
        for item in sorted(self.target.backup_dir.glob("*.bak"), key=lambda path: path.stat().st_mtime, reverse=True):
            stat = item.stat()
            backups.append(
                {
                    "filename": item.name,
                    "path": str(item),
                    "size_bytes": stat.st_size,
                    "sha256": file_sha256(item),
                    "created_at": datetime.fromtimestamp(stat.st_mtime).astimezone(),
                }
            )
        return {
            "database_path": str(self.target.database_path),
            "backup_dir": str(self.target.backup_dir),
            "backups": backups,
        }

    def create_backup(self, actor: str = "local_user") -> dict[str, Any]:
        source = self.target.database_path
        if not source.exists():
            raise HTTPException(status_code=404, detail=f"Database file not found: {source}")
        self.target.backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = utcnow().strftime("%Y%m%d-%H%M%S-%f")
        target = self.target.backup_dir / f"{source.stem}-{timestamp}{source.suffix}.bak"
        if target.exists():
            raise HTTPException(status_code=409, detail=f"Backup already exists: {target.name}")
        shutil.copy2(source, target)
        sha256 = file_sha256(target)
        event = self._record_event(
            event_type="BACKUP_CREATED",
            artifact=target,
            artifact_sha256=sha256,
            reason="Manual backup",
            actor=actor,
            metadata={"database_path": str(source), "size_bytes": target.stat().st_size},
        )
        return {
            "filename": target.name,
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "sha256": sha256,
            "created_at": datetime.fromtimestamp(target.stat().st_mtime).astimezone(),
            "event_id": event.id,
        }

    def restore_backup(self, filename: str, confirmation_text: str, reason: str, actor: str = "local_user") -> dict[str, Any]:
        if confirmation_text != "RESTORE":
            raise HTTPException(status_code=422, detail="confirmation_text must be RESTORE")
        backup = self._backup_path(filename)
        self._validate_backup(backup)
        source = self.target.database_path
        self.target.backup_dir.mkdir(parents=True, exist_ok=True)
        pre_restore_backup: Path | None = None
        if source.exists():
            timestamp = utcnow().strftime("%Y%m%d-%H%M%S-%f")
            pre_restore_backup = self.target.backup_dir / f"{source.stem}-pre-restore-{timestamp}{source.suffix}.bak"
            shutil.copy2(source, pre_restore_backup)

        app_engine.dispose()
        shutil.copy2(backup, source)
        app_engine.dispose()

        restored_sha256 = file_sha256(source)
        event = self._record_event(
            event_type="RESTORE_COMPLETED",
            artifact=backup,
            artifact_sha256=file_sha256(backup),
            reason=reason,
            actor=actor,
            metadata={
                "restored_to": str(source),
                "restored_sha256": restored_sha256,
                "pre_restore_backup": str(pre_restore_backup) if pre_restore_backup else None,
            },
        )
        return {
            "restored_from": str(backup),
            "restored_to": str(source),
            "restored_sha256": restored_sha256,
            "pre_restore_backup": str(pre_restore_backup) if pre_restore_backup else None,
            "event_id": event.id,
            "restored_at": event.created_at,
        }

    def _backup_path(self, filename: str) -> Path:
        if Path(filename).name != filename:
            raise HTTPException(status_code=422, detail="filename must not include a path")
        backup = (self.target.backup_dir / filename).resolve()
        if self.target.backup_dir not in backup.parents and backup != self.target.backup_dir:
            raise HTTPException(status_code=422, detail="Backup path escapes backup directory")
        if not backup.exists() or not backup.is_file():
            raise HTTPException(status_code=404, detail=f"Backup not found: {filename}")
        return backup

    def _validate_backup(self, backup: Path) -> None:
        try:
            with sqlite3.connect(f"file:{backup.as_posix()}?mode=ro", uri=True) as connection:
                quick_check = connection.execute("PRAGMA quick_check").fetchone()
                if quick_check is None or quick_check[0] != "ok":
                    raise HTTPException(status_code=422, detail="SQLite backup failed PRAGMA quick_check")
                version_row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
                if version_row is None or version_row[0] != CURRENT_ALEMBIC_VERSION:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Backup database version must be {CURRENT_ALEMBIC_VERSION}",
                    )
        except sqlite3.DatabaseError as exc:
            raise HTTPException(status_code=422, detail=f"Invalid SQLite backup: {exc}") from exc

    def _record_event(
        self,
        event_type: str,
        artifact: Path,
        artifact_sha256: str,
        reason: str | None,
        actor: str,
        metadata: dict[str, Any],
    ) -> SafetyEvent:
        engine = create_app_engine(self.database_url)
        Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
        with Session() as session:
            event = SafetyEvent(
                event_type=event_type,
                artifact_name=artifact.name,
                artifact_path=str(artifact),
                artifact_sha256=artifact_sha256,
                reason=reason,
                actor=actor,
                event_metadata=metadata,
            )
            session.add(event)
            session.commit()
            session.refresh(event)
            return event


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
