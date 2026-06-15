from __future__ import annotations

from sqlalchemy import func, select, text
from sqlalchemy.orm import sessionmaker

from app.core.database import create_app_engine
from fastapi import HTTPException

from app.models import Base, Bottle, Cellar, Location, Producer, SafetyEvent, Vintage, Wine
from app.schemas.common import BottleCreate, InventoryTransactionCreate
from app.services.analytics_service import AnalyticsService
from app.services.collection_service import CollectionSearchFilters, CollectionService
from app.services.inventory_service import InventoryService
from app.services.safety_service import SafetyService


def test_backup_creation_uses_unique_timestamped_files_and_records_events(tmp_path) -> None:
    database_url = _create_safety_database(tmp_path / "safety-backup.db")
    service = SafetyService(database_url=database_url)

    first = service.create_backup()
    second = service.create_backup()
    listing = service.list_backups()

    assert first["filename"] != second["filename"]
    assert first["filename"].endswith(".db.bak")
    assert second["filename"].endswith(".db.bak")
    assert len(listing["backups"]) == 2
    assert all(item["sha256"] for item in listing["backups"])

    engine = create_app_engine(database_url)
    Session = sessionmaker(bind=engine)
    with Session() as session:
        events = session.scalar(select(func.count(SafetyEvent.id)).where(SafetyEvent.event_type == "BACKUP_CREATED"))
    assert events == 2


def test_restore_requires_confirmation_and_restores_inventory_timeline_and_analytics(tmp_path) -> None:
    database_url = _create_safety_database(tmp_path / "safety-restore.db")
    service = SafetyService(database_url=database_url)
    backup = service.create_backup()

    engine = create_app_engine(database_url)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with Session() as session:
        bottle_id = session.scalar(select(Bottle.id).limit(1))
        assert bottle_id is not None
        transaction = InventoryService(session).apply_transaction(
            InventoryTransactionCreate(
                bottle_id=bottle_id,
                transaction_type="CONSUME",
                actor="test",
                note="mutation after backup",
            )
        )
        assert transaction.transaction_type == "CONSUME"
        assert AnalyticsService(session).summary()["inventory"]["status_distribution"][0]["label"] == "drunk"

    bad_restore = None
    try:
        service.restore_backup(
            filename=backup["filename"],
            confirmation_text="restore",
            reason="wrong confirmation",
        )
    except HTTPException as exc:
        bad_restore = exc
    assert bad_restore is not None

    restored = service.restore_backup(
        filename=backup["filename"],
        confirmation_text="RESTORE",
        reason="restore test backup",
    )

    assert restored["event_id"]
    assert restored["pre_restore_backup"]
    assert restored["restored_sha256"] == backup["sha256"]

    restored_engine = create_app_engine(database_url)
    RestoredSession = sessionmaker(bind=restored_engine)
    with RestoredSession() as session:
        analytics = AnalyticsService(session).summary()
        assert analytics["inventory"]["total_bottles"] == 1
        assert analytics["inventory"]["status_distribution"] == [{"label": "in_stock", "count": 1}]

        collection = CollectionService(session).search(CollectionSearchFilters(query="Safety"))
        assert collection["total"] == 1
        bottle_id = collection["items"][0]["bottle_id"]
        timeline = CollectionService(session).bottle_timeline(bottle_id)
        assert timeline is not None
        assert [event["event_type"] for event in timeline] == ["IN"]

        events = session.scalars(select(SafetyEvent).order_by(SafetyEvent.created_at)).all()
        assert len(events) == 1
        assert events[0].event_type == "RESTORE_COMPLETED"
        assert events[0].reason == "restore test backup"


def _create_safety_database(path) -> str:
    database_url = f"sqlite:///{path}"
    engine = create_app_engine(database_url)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)"))
        connection.execute(text("INSERT INTO alembic_version (version_num) VALUES ('20260614_0005')"))
    with Session() as session:
        cellar = Cellar(name="Safety Cellar", cellar_type="cabinet")
        producer = Producer(name_original="Safety Estate", country="France")
        session.add_all([cellar, producer])
        session.flush()
        location = Location(cellar_id=cellar.id, code="SAFE-01", capacity=1)
        session.add(location)
        session.flush()
        wine = Wine(producer_id=producer.id, name_original="Safety Rouge", country="France")
        session.add(wine)
        session.flush()
        vintage = Vintage(wine_id=wine.id, vintage_year=2020, is_non_vintage=False)
        session.add(vintage)
        session.flush()
        InventoryService(session).create_bottle_with_in_transaction(
            BottleCreate(vintage_id=vintage.id, current_location_id=location.id, actor="test"),
        )
    return database_url
