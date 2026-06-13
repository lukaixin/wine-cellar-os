from __future__ import annotations

import argparse
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy.engine import make_url

from app.core.config import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up the local SQLite database without modifying it.")
    parser.add_argument("--database-url", default=get_settings().database_url)
    parser.add_argument("--backup-dir", default=None)
    args = parser.parse_args()

    source = _sqlite_path(args.database_url)
    if source is None:
        raise SystemExit("Only file-based SQLite database URLs can be backed up by this script.")
    if not source.exists():
        print(f"No database file found at {source}; nothing to back up.")
        return

    backup_dir = Path(args.backup_dir) if args.backup_dir else source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{source.stem}-{timestamp}{source.suffix}.bak"
    shutil.copy2(source, target)
    print(f"Backed up {source} -> {target}")


def _sqlite_path(database_url: str) -> Path | None:
    url = make_url(database_url)
    if url.drivername not in {"sqlite", "sqlite+pysqlite"} or not url.database or url.database == ":memory:":
        return None
    return Path(url.database).expanduser().resolve()


if __name__ == "__main__":
    main()
