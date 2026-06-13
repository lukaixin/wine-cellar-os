from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.core.database import create_app_engine
from app.models import (
    Base,
    Bottle,
    Cellar,
    DrinkWindow,
    InventoryTransaction,
    LabelImageUpload,
    Location,
    MediaAsset,
    ObjectTag,
    Producer,
    Tag,
    ValuationSnapshot,
    Vintage,
    Wine,
)


def make_session(tmp_path):
    engine = create_app_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory()


def test_schema_creates_core_tables(tmp_path) -> None:
    engine, session = make_session(tmp_path)
    try:
        table_names = set(inspect(engine).get_table_names())

        assert {
            "producers",
            "wines",
            "vintages",
            "cellars",
            "locations",
            "bottles",
            "inventory_transactions",
            "label_image_uploads",
            "valuation_snapshots",
            "drink_windows",
            "media_assets",
            "tags",
            "object_tags",
        }.issubset(table_names)

        bottle_fk_tables = {fk["referred_table"] for fk in inspect(engine).get_foreign_keys("bottles")}
        transaction_fk_tables = {
            fk["referred_table"] for fk in inspect(engine).get_foreign_keys("inventory_transactions")
        }

        assert {"vintages", "locations"}.issubset(bottle_fk_tables)
        assert {"bottles", "locations"}.issubset(transaction_fk_tables)
        label_upload_fk_tables = {fk["referred_table"] for fk in inspect(engine).get_foreign_keys("label_image_uploads")}
        assert "bottles" in label_upload_fk_tables
    finally:
        session.close()


def test_basic_model_relationships_round_trip(tmp_path) -> None:
    _, session = make_session(tmp_path)
    try:
        producer = Producer(name_original="Chateau Example", name_cn="示例酒庄", country="France")
        wine = Wine(producer=producer, name_original="Grand Vin", type="red", aliases=["正牌"])
        vintage = Vintage(wine=wine, vintage_year=2018, is_non_vintage=False)
        cellar = Cellar(name="A柜", cellar_type="cabinet", rows=6, columns=8)
        location = Location(cellar=cellar, code="A-01-01", row_index=1, column_index=1, capacity=2)
        bottle = Bottle(
            vintage=vintage,
            bottle_size_ml=750,
            acquisition_date=date(2026, 6, 12),
            purchase_price=Decimal("388.00"),
            purchase_currency="CNY",
            current_status="in_stock",
            current_location=location,
        )
        transaction = InventoryTransaction(
            bottle=bottle,
            transaction_type="IN",
            to_location=location,
            actor="manual",
        )
        drink_window = DrinkWindow(vintage=vintage, source="manual", drink_from=2026, drink_to=2032, confidence="low")
        valuation = ValuationSnapshot(
            vintage=vintage,
            source="manual",
            currency="CNY",
            avg_price=Decimal("450.00"),
            confidence="low",
        )
        tag = Tag(name="请客稳妥", category="occasion")

        session.add_all([producer, cellar, bottle, transaction, drink_window, valuation, tag])
        session.commit()

        object_tag = ObjectTag(tag=tag, owner_type="bottle", owner_id=bottle.id)
        media = MediaAsset(
            owner_type="bottle",
            owner_id=bottle.id,
            media_type="front_label",
            file_path="assets/label-images/example.jpg",
        )
        label_upload = LabelImageUpload(
            original_filename="example-label.jpg",
            stored_filename="uuid-example-label.jpg",
            content_type="image/jpeg",
            size_bytes=12,
            sha256="0" * 64,
            file_path="uploads/labels/uuid-example-label.jpg",
            bottle=bottle,
        )
        session.add_all([object_tag, media, label_upload])
        session.commit()

        saved = session.get(Bottle, bottle.id)

        assert saved is not None
        assert saved.vintage.wine.producer.name_cn == "示例酒庄"
        assert saved.current_location.cellar.name == "A柜"
        assert saved.transactions[0].transaction_type == "IN"
        assert saved.vintage.drink_windows[0].drink_to == 2032
        assert saved.vintage.valuation_snapshots[0].avg_price == Decimal("450.00")
        assert tag.object_tags[0].owner_id == saved.id
        assert label_upload.bottle_id == saved.id
    finally:
        session.close()


def test_inventory_transaction_requires_location_by_type(tmp_path) -> None:
    _, session = make_session(tmp_path)
    try:
        producer = Producer(name_original="Chateau Example")
        wine = Wine(producer=producer, name_original="Grand Vin")
        vintage = Vintage(wine=wine, vintage_year=2019, is_non_vintage=False)
        bottle = Bottle(vintage=vintage, current_status="in_stock")
        session.add_all([producer, bottle])
        session.commit()

        session.add(InventoryTransaction(bottle=bottle, transaction_type="IN"))

        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()


def test_drink_window_rejects_invalid_range(tmp_path) -> None:
    _, session = make_session(tmp_path)
    try:
        producer = Producer(name_original="Chateau Example")
        wine = Wine(producer=producer, name_original="Grand Vin")
        vintage = Vintage(wine=wine, vintage_year=2020, is_non_vintage=False)
        session.add_all([producer, vintage])
        session.commit()

        session.add(DrinkWindow(vintage=vintage, source="manual", drink_from=2030, drink_to=2025, confidence="low"))

        with pytest.raises(IntegrityError):
            session.commit()
    finally:
        session.close()
