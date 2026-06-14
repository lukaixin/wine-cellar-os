from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_app_engine(f"sqlite:///{tmp_path / 'analytics-test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_analytics_summary_aggregates_inventory_ws_price_and_ledger_activity(client: TestClient) -> None:
    ids = _create_analytics_fixture(client)

    client.post("/inventory/actions/consume", json={"bottle_id": ids["consume_bottle_id"], "quantity": 1})
    client.post(
        "/inventory/actions/gift",
        json={"bottle_id": ids["gift_bottle_id"], "quantity": 1, "recipient": "朋友"},
    )
    client.post(
        "/inventory/actions/damage",
        json={"bottle_id": ids["damage_bottle_id"], "quantity": 1, "reason": "破损"},
    )

    response = client.get("/api/analytics/summary")

    assert response.status_code == 200
    body = response.json()
    inventory = body["inventory"]
    assert inventory["total_bottles"] == 3
    assert inventory["total_wines"] == 1
    assert inventory["total_producers"] == 1
    assert inventory["total_vintages"] == 1
    assert inventory["total_ws_value"] == "300.00"
    assert inventory["ws_priced_bottles"] == 2
    assert inventory["country_distribution"] == [{"label": "France", "count": 3}]
    assert {"label": "drunk", "count": 1} in inventory["status_distribution"]
    assert {"label": "gifted", "count": 1} in inventory["status_distribution"]
    assert {"label": "damaged", "count": 1} in inventory["status_distribution"]

    all_time = next(item for item in body["consumption"]["periods"] if item["key"] == "all_time")
    assert all_time == {
        "key": "all_time",
        "label": "All Time",
        "consumed_bottles": 1,
        "gifted_bottles": 1,
        "damaged_bottles": 1,
    }
    assert body["consumption"]["monthly_trend"][-1]["consumed_bottles"] == 1
    assert {item["event_type"] for item in body["activity"]} >= {"IMPORT", "CONSUME", "GIFT", "DAMAGE"}


def _create_analytics_fixture(client: TestClient) -> dict[str, str]:
    producer = client.post("/api/producers", json={"name_original": "Analytics Estate", "country": "France"}).json()
    wine = client.post(
        "/api/wines",
        json={
            "producer_id": producer["id"],
            "name_original": "Analytics Rouge",
            "country": "France",
            "region": "Bordeaux",
        },
    ).json()
    vintage = client.post("/api/vintages", json={"wine_id": wine["id"], "vintage_year": 2020}).json()
    cellar = client.post("/api/cellars", json={"name": "Analytics Cellar", "cellar_type": "cabinet"}).json()
    locations = client.post(
        f"/api/cellars/{cellar['id']}/locations/batch",
        json={"rows": 1, "columns": 3, "code_prefix": "AN", "capacity": 1},
    ).json()
    bottle_ids = []
    for index, ws_price in enumerate(["100.00", "200.00", None]):
        bottle = client.post(
            "/api/bottles",
            json={
                "vintage_id": vintage["id"],
                "current_location_id": locations[index]["id"],
                "ws_price": ws_price,
            },
        )
        assert bottle.status_code == 201
        bottle_ids.append(bottle.json()["id"])
    return {
        "consume_bottle_id": bottle_ids[0],
        "gift_bottle_id": bottle_ids[1],
        "damage_bottle_id": bottle_ids[2],
    }
