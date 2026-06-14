from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base, Bottle, Cellar, Location, Producer, Vintage, Wine
from app.services.registry_service import RegistryService


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_app_engine(f"sqlite:///{tmp_path / 'collection-explorer-test.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


@pytest.fixture()
def client(session_factory) -> Generator[TestClient, None, None]:
    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_collection_search_returns_bottle_groups_for_registry_matches(
    client: TestClient,
    session_factory,
) -> None:
    ids = _create_collection_fixture(client, session_factory)

    response = client.get("/collection/search?q=DRC&status=in_stock")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    row = body["items"][0]
    assert row["producer_name"] == "Domaine de la Romanee-Conti"
    assert row["wine_name"] == "Romanee-Conti Grand Cru"
    assert row["vintage_year"] == 2020
    assert row["bottle_count"] == 2
    assert row["location"]["code"] == "A-01-01"
    assert row["status"] == "in_stock"
    assert set(row["bottle_ids"]) == {ids["drc_bottle_a_id"], ids["drc_bottle_b_id"]}


def test_collection_search_supports_allowed_filters(client: TestClient, session_factory) -> None:
    ids = _create_collection_fixture(client, session_factory)

    by_producer = client.get(f"/collection/search?producer_id={ids['rayas_producer_id']}").json()
    by_vintage = client.get("/collection/search?vintage_year=2016").json()
    by_location = client.get(f"/collection/search?location_id={ids['location_b_id']}").json()
    by_status = client.get("/collection/search?status=drunk").json()

    assert by_producer["total"] == 1
    assert by_producer["items"][0]["producer_name"] == "Chateau Rayas"
    assert by_vintage["total"] == 1
    assert by_vintage["items"][0]["vintage_year"] == 2016
    assert by_location["total"] == 1
    assert by_location["items"][0]["location"]["code"] == "B-01-01"
    assert by_status["total"] == 1
    assert by_status["items"][0]["bottle_id"] == ids["drunk_bottle_id"]


def test_collection_search_paginates_grouped_results(client: TestClient, session_factory) -> None:
    _create_collection_fixture(client, session_factory)

    first = client.get("/collection/search?limit=1&offset=0").json()
    second = client.get("/collection/search?limit=1&offset=1").json()

    assert first["total"] == 3
    assert first["limit"] == 1
    assert first["offset"] == 0
    assert len(first["items"]) == 1
    assert second["offset"] == 1
    assert len(second["items"]) == 1
    assert first["items"][0]["bottle_id"] != second["items"][0]["bottle_id"]


def test_collection_bottle_detail_is_limited_to_collection_fields(client: TestClient, session_factory) -> None:
    ids = _create_collection_fixture(client, session_factory)

    response = client.get(f"/collection/bottles/{ids['drc_bottle_a_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["bottle_id"] == ids["drc_bottle_a_id"]
    assert body["producer_name"] == "Domaine de la Romanee-Conti"
    assert body["wine_name"] == "Romanee-Conti Grand Cru"
    assert body["quantity"] == 1
    assert body["location"]["cellar_name"] == "主柜"
    assert body["location"]["code"] == "A-01-01"
    assert body["acquisition_date"] == "2026-06-13"
    assert "purchase_price" not in body
    assert "default_drink_from" not in body


def test_collection_bottle_detail_404s_for_missing_bottle(client: TestClient) -> None:
    response = client.get("/collection/bottles/missing")

    assert response.status_code == 404


def test_collection_bottle_timeline_returns_ledger_events_desc(client: TestClient, session_factory) -> None:
    ids = _create_collection_fixture(client, session_factory)

    move_response = client.post(
        "/api/inventory-transactions",
        json={
            "bottle_id": ids["drc_bottle_a_id"],
            "transaction_type": "MOVE",
            "to_location_id": ids["location_b_id"],
            "occurred_at": "2026-06-14T10:00:00Z",
            "note": "Location changed for detail timeline",
        },
    )
    assert move_response.status_code == 201

    response = client.get(f"/collection/bottles/{ids['drc_bottle_a_id']}/timeline")

    assert response.status_code == 200
    body = response.json()
    assert [event["event_type"] for event in body] == ["MOVE", "IN"]
    assert body[0]["quantity_delta"] == 0
    assert body[0]["reference_type"] == "inventory_transaction"
    assert body[0]["reference_id"] == move_response.json()["id"]
    assert body[0]["from_location"]["code"] == "A-01-01"
    assert body[0]["to_location"]["code"] == "B-01-01"
    assert body[0]["notes"] == "Location changed for detail timeline"
    assert body[1]["quantity_delta"] == 1


def test_collection_bottle_timeline_is_empty_when_bottle_has_no_ledger(client: TestClient, session_factory) -> None:
    bottle_id = _create_bottle_without_transactions(session_factory)

    response = client.get(f"/collection/bottles/{bottle_id}/timeline")

    assert response.status_code == 200
    assert response.json() == []


def test_collection_bottle_timeline_404s_for_missing_bottle(client: TestClient) -> None:
    response = client.get("/collection/bottles/missing/timeline")

    assert response.status_code == 404


def _create_collection_fixture(client: TestClient, session_factory) -> dict[str, str]:
    cellar = client.post("/api/cellars", json={"name": "主柜", "cellar_type": "cabinet"}).json()
    location_a = client.post("/api/locations", json={"cellar_id": cellar["id"], "code": "A-01-01", "capacity": 2}).json()
    location_b = client.post("/api/locations", json={"cellar_id": cellar["id"], "code": "B-01-01", "capacity": 2}).json()

    drc_producer = client.post(
        "/api/producers",
        json={"name_original": "Domaine de la Romanee-Conti", "name_cn": "罗曼尼康帝"},
    ).json()
    drc_wine = client.post(
        "/api/wines",
        json={
            "producer_id": drc_producer["id"],
            "name_original": "Romanee-Conti Grand Cru",
            "name_cn": "罗曼尼康帝特级园",
            "country": "France",
            "region": "Bourgogne",
        },
    ).json()
    drc_vintage = client.post("/api/vintages", json={"wine_id": drc_wine["id"], "vintage_year": 2020}).json()
    drc_bottle_a = client.post(
        "/api/bottles",
        json={
            "vintage_id": drc_vintage["id"],
            "current_location_id": location_a["id"],
            "acquisition_date": "2026-06-13",
            "purchase_price": "100.00",
        },
    ).json()
    drc_bottle_b = client.post(
        "/api/bottles",
        json={"vintage_id": drc_vintage["id"], "current_location_id": location_a["id"]},
    ).json()

    rayas_producer = client.post("/api/producers", json={"name_original": "Chateau Rayas"}).json()
    rayas_wine = client.post(
        "/api/wines",
        json={"producer_id": rayas_producer["id"], "name_original": "Chateauneuf-du-Pape Reserve"},
    ).json()
    rayas_vintage = client.post("/api/vintages", json={"wine_id": rayas_wine["id"], "vintage_year": 2016}).json()
    rayas_bottle = client.post(
        "/api/bottles",
        json={"vintage_id": rayas_vintage["id"], "current_location_id": location_b["id"]},
    ).json()

    drunk_bottle = client.post(
        "/api/bottles",
        json={"vintage_id": drc_vintage["id"], "current_location_id": location_b["id"]},
    ).json()
    client.post(
        "/api/inventory-transactions",
        json={"bottle_id": drunk_bottle["id"], "transaction_type": "CONSUME", "note": "tasted"},
    )

    with session_factory() as session:
        registry = RegistryService(session)
        producer = session.get(Producer, drc_producer["id"])
        assert producer is not None
        registry.record_alias(entity_type="producer", entity_id=producer.id, alias_text="DRC", status="approved")
        session.commit()

    return {
        "location_b_id": location_b["id"],
        "rayas_producer_id": rayas_producer["id"],
        "drc_bottle_a_id": drc_bottle_a["id"],
        "drc_bottle_b_id": drc_bottle_b["id"],
        "rayas_bottle_id": rayas_bottle["id"],
        "drunk_bottle_id": drunk_bottle["id"],
    }


def _create_bottle_without_transactions(session_factory) -> str:
    with session_factory() as session:
        cellar = Cellar(name="No Ledger Cellar", cellar_type="cabinet")
        session.add(cellar)
        session.flush()
        location = Location(cellar_id=cellar.id, code="NL-01", capacity=1)
        producer = Producer(name_original="No Ledger Estate")
        session.add_all([location, producer])
        session.flush()
        wine = Wine(producer_id=producer.id, name_original="No Ledger Wine")
        session.add(wine)
        session.flush()
        vintage = Vintage(wine_id=wine.id, vintage_year=2021, is_non_vintage=False)
        session.add(vintage)
        session.flush()
        bottle = Bottle(
            vintage_id=vintage.id,
            bottle_size_ml=750,
            current_status="in_stock",
            current_location_id=location.id,
            purchase_currency="CNY",
            created_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
            updated_at=datetime(2026, 6, 14, tzinfo=timezone.utc),
        )
        session.add(bottle)
        session.commit()
        return bottle.id
