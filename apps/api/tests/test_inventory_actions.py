from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base, Bottle, InventoryTransaction


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_app_engine(f"sqlite:///{tmp_path / 'inventory-actions-test.db'}")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    def override_get_session() -> Generator[Session, None, None]:
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        with TestClient(app) as test_client:
            test_client.session_factory = session_factory  # type: ignore[attr-defined]
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_consume_action_writes_ledger_and_updates_bottle(client: TestClient) -> None:
    ids = _create_inventory_fixture(client)
    bottle_id = _create_bottle(client, ids["vintage_id"], ids["location_a_id"])

    response = client.post(
        "/inventory/actions/consume",
        json={"bottle_id": bottle_id, "quantity": 1, "notes": "Weekend dinner"},
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "CONSUME"
    assert response.json()["from_location_id"] == ids["location_a_id"]
    bottle = client.get(f"/api/bottles/{bottle_id}").json()
    assert bottle["current_status"] == "drunk"
    assert bottle["current_location_id"] is None

    timeline = client.get(f"/collection/bottles/{bottle_id}/timeline").json()
    assert timeline[0]["event_type"] == "CONSUME"
    assert timeline[0]["quantity_delta"] == -1
    assert timeline[0]["notes"] == "Weekend dinner"


def test_gift_action_records_recipient_in_ledger_timeline(client: TestClient) -> None:
    ids = _create_inventory_fixture(client)
    bottle_id = _create_bottle(client, ids["vintage_id"], ids["location_a_id"])

    response = client.post(
        "/inventory/actions/gift",
        json={"bottle_id": bottle_id, "quantity": 1, "recipient": "John", "notes": "Birthday"},
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "GIFT"
    assert response.json()["reason"] == "Recipient: John"
    bottle = client.get(f"/api/bottles/{bottle_id}").json()
    assert bottle["current_status"] == "gifted"
    assert bottle["current_location_id"] is None
    assert client.get(f"/collection/bottles/{bottle_id}/timeline").json()[0]["notes"] == "Recipient: John · Birthday"


def test_damage_action_records_reason_and_prevents_reuse(client: TestClient) -> None:
    ids = _create_inventory_fixture(client)
    bottle_id = _create_bottle(client, ids["vintage_id"], ids["location_a_id"])

    response = client.post(
        "/api/inventory/actions/damage",
        json={"bottle_id": bottle_id, "quantity": 1, "reason": "Cork damage", "notes": "Leaked in storage"},
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "DAMAGE"
    assert response.json()["reason"] == "Cork damage"
    assert client.get(f"/api/bottles/{bottle_id}").json()["current_status"] == "damaged"

    duplicate = client.post(
        "/inventory/actions/consume",
        json={"bottle_id": bottle_id, "quantity": 1, "notes": "Should fail"},
    )
    assert duplicate.status_code == 409
    assert "already unavailable" in duplicate.json()["detail"]


def test_move_action_validates_locations_and_refreshes_timeline_source(client: TestClient) -> None:
    ids = _create_inventory_fixture(client)
    bottle_id = _create_bottle(client, ids["vintage_id"], ids["location_a_id"])

    response = client.post(
        "/inventory/actions/move",
        json={
            "bottle_id": bottle_id,
            "from_location": ids["location_a_id"],
            "to_location": ids["location_b_id"],
            "notes": "Cabinet B",
        },
    )

    assert response.status_code == 201
    assert response.json()["transaction_type"] == "MOVE"
    bottle = client.get(f"/collection/bottles/{bottle_id}").json()
    assert bottle["status"] == "in_stock"
    assert bottle["location"]["id"] == ids["location_b_id"]
    timeline = client.get(f"/collection/bottles/{bottle_id}/timeline").json()
    assert timeline[0]["event_type"] == "MOVE"
    assert timeline[0]["from_location"]["code"] == "A-01"
    assert timeline[0]["to_location"]["code"] == "B-01"


def test_actions_reject_invalid_quantities_and_bad_locations(client: TestClient) -> None:
    ids = _create_inventory_fixture(client)
    bottle_id = _create_bottle(client, ids["vintage_id"], ids["location_a_id"])

    zero_quantity = client.post(
        "/inventory/actions/consume",
        json={"bottle_id": bottle_id, "quantity": 0, "notes": "invalid"},
    )
    assert zero_quantity.status_code == 422

    over_quantity = client.post(
        "/inventory/actions/consume",
        json={"bottle_id": bottle_id, "quantity": 2, "notes": "invalid"},
    )
    assert over_quantity.status_code == 422
    assert "quantity must be 1" in over_quantity.json()["detail"]

    stale_move = client.post(
        "/inventory/actions/move",
        json={
            "bottle_id": bottle_id,
            "from_location": ids["location_b_id"],
            "to_location": ids["location_c_id"],
            "notes": "stale page",
        },
    )
    assert stale_move.status_code == 409
    assert "from_location_id" in stale_move.json()["detail"]

    missing_location = client.post(
        "/inventory/actions/move",
        json={
            "bottle_id": bottle_id,
            "from_location": ids["location_a_id"],
            "to_location": "missing-location",
            "notes": "invalid target",
        },
    )
    assert missing_location.status_code == 404


def test_action_endpoints_do_not_mutate_without_ledger(client: TestClient) -> None:
    ids = _create_inventory_fixture(client)
    bottle_id = _create_bottle(client, ids["vintage_id"], ids["location_a_id"])

    response = client.post(
        "/inventory/actions/gift",
        json={"bottle_id": bottle_id, "quantity": 1, "recipient": "John"},
    )
    assert response.status_code == 201

    session_factory = client.session_factory  # type: ignore[attr-defined]
    with session_factory() as session:
        bottle = session.get(Bottle, bottle_id)
        assert bottle is not None
        transactions = session.query(InventoryTransaction).filter_by(bottle_id=bottle_id).all()
        assert bottle.current_status == "gifted"
        assert [transaction.transaction_type for transaction in transactions] == ["IN", "GIFT"]


def _create_inventory_fixture(client: TestClient) -> dict[str, str]:
    producer = client.post("/api/producers", json={"name_original": "Action Estate"})
    assert producer.status_code == 201
    wine = client.post("/api/wines", json={"producer_id": producer.json()["id"], "name_original": "Action Red"})
    assert wine.status_code == 201
    vintage = client.post("/api/vintages", json={"wine_id": wine.json()["id"], "vintage_year": 2020})
    assert vintage.status_code == 201
    cellar = client.post("/api/cellars", json={"name": "Action Cellar", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    location_a = client.post("/api/locations", json={"cellar_id": cellar.json()["id"], "code": "A-01", "capacity": 4})
    assert location_a.status_code == 201
    location_b = client.post("/api/locations", json={"cellar_id": cellar.json()["id"], "code": "B-01", "capacity": 4})
    assert location_b.status_code == 201
    location_c = client.post("/api/locations", json={"cellar_id": cellar.json()["id"], "code": "C-01", "capacity": 4})
    assert location_c.status_code == 201
    return {
        "vintage_id": vintage.json()["id"],
        "location_a_id": location_a.json()["id"],
        "location_b_id": location_b.json()["id"],
        "location_c_id": location_c.json()["id"],
    }


def _create_bottle(client: TestClient, vintage_id: str, location_id: str) -> str:
    response = client.post("/api/bottles", json={"vintage_id": vintage_id, "current_location_id": location_id})
    assert response.status_code == 201
    return response.json()["id"]
