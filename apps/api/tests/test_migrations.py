from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.models import Base


API_DIR = Path(__file__).resolve().parents[1]


def _alembic_config(database_url: str) -> Config:
    config = Config(str(API_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(API_DIR / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_alembic_upgrade_creates_schema_from_empty_sqlite(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration-empty.db'}"
    monkeypatch.setenv("WINE_CELLAR_DATABASE_URL", database_url)

    command.upgrade(_alembic_config(database_url), "head")

    engine = create_engine(database_url)
    tables = set(inspect(engine).get_table_names())
    assert {
        "alembic_version",
        "producers",
        "wines",
        "vintages",
        "bottles",
        "inventory_transactions",
        "cellars",
        "locations",
        "label_image_uploads",
        "import_batches",
        "import_batch_rows",
    }.issubset(tables)


def test_alembic_upgrade_stamps_existing_alpha_sqlite_without_deleting_data(tmp_path, monkeypatch) -> None:
    database_url = f"sqlite:///{tmp_path / 'migration-existing.db'}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    now = datetime.now(timezone.utc).isoformat()
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO producers (id, name_original, created_at, updated_at)
                VALUES (:id, :name_original, :created_at, :updated_at)
                """
            ),
            {
                "id": "producer-existing",
                "name_original": "Existing Estate",
                "created_at": now,
                "updated_at": now,
            },
        )
    monkeypatch.setenv("WINE_CELLAR_DATABASE_URL", database_url)

    command.upgrade(_alembic_config(database_url), "head")

    with engine.connect() as connection:
        producer_count = connection.execute(text("SELECT COUNT(*) FROM producers")).scalar_one()
        version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert producer_count == 1
    assert version == "20260613_0002"
