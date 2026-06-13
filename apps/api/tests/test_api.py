from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_app_engine(f"sqlite:///{tmp_path / 'api-test.db'}")
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


def create_minimum_inventory(client: TestClient) -> dict[str, str]:
    producer = client.post("/api/producers", json={"name_original": "Chateau Test", "name_cn": "测试酒庄"})
    assert producer.status_code == 201
    wine = client.post(
        "/api/wines",
        json={"producer_id": producer.json()["id"], "name_original": "Grand Vin", "type": "red"},
    )
    assert wine.status_code == 201
    vintage = client.post(
        "/api/vintages",
        json={"wine_id": wine.json()["id"], "vintage_year": 2020, "is_non_vintage": False},
    )
    assert vintage.status_code == 201
    cellar = client.post("/api/cellars", json={"name": "A柜", "cellar_type": "cabinet", "rows": 2, "columns": 2})
    assert cellar.status_code == 201
    location = client.post(
        "/api/locations",
        json={"cellar_id": cellar.json()["id"], "code": "A-01-01", "row_index": 1, "column_index": 1},
    )
    assert location.status_code == 201
    return {
        "producer_id": producer.json()["id"],
        "wine_id": wine.json()["id"],
        "vintage_id": vintage.json()["id"],
        "cellar_id": cellar.json()["id"],
        "location_id": location.json()["id"],
    }


def test_health_still_works(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_crud_and_bottle_create_writes_in_transaction(client: TestClient) -> None:
    ids = create_minimum_inventory(client)

    bottle = client.post(
        "/api/bottles",
        json={
            "vintage_id": ids["vintage_id"],
            "current_location_id": ids["location_id"],
            "purchase_price": "399.00",
            "purchase_currency": "CNY",
            "actor": "manual",
            "note": "首次入库",
        },
    )

    assert bottle.status_code == 201
    bottle_body = bottle.json()
    assert bottle_body["current_status"] == "in_stock"
    assert bottle_body["location_code"] == "A-01-01"
    assert bottle_body["producer_name_cn"] == "测试酒庄"

    transactions = client.get(f"/api/bottles/{bottle_body['id']}/transactions")
    assert transactions.status_code == 200
    assert len(transactions.json()) == 1
    assert transactions.json()[0]["transaction_type"] == "IN"


def test_transaction_workflow_moves_and_consumes_bottle(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    location2 = client.post(
        "/api/locations",
        json={"cellar_id": ids["cellar_id"], "code": "A-01-02", "row_index": 1, "column_index": 2},
    )
    assert location2.status_code == 201
    bottle = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    )
    bottle_id = bottle.json()["id"]

    move = client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": "MOVE", "to_location_id": location2.json()["id"]},
    )
    assert move.status_code == 201
    assert move.json()["from_location_code"] == "A-01-01"
    assert move.json()["to_location_code"] == "A-01-02"
    assert client.get(f"/api/bottles/{bottle_id}").json()["location_code"] == "A-01-02"

    consume = client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": "CONSUME", "note": "周末晚餐"},
    )
    assert consume.status_code == 201
    body = client.get(f"/api/bottles/{bottle_id}").json()
    assert body["current_status"] == "drunk"
    assert body["current_location_id"] is None


def test_move_rejects_stale_from_location_and_same_target(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    location2 = client.post(
        "/api/locations",
        json={"cellar_id": ids["cellar_id"], "code": "A-01-02", "row_index": 1, "column_index": 2},
    ).json()
    location3 = client.post(
        "/api/locations",
        json={"cellar_id": ids["cellar_id"], "code": "A-01-03", "row_index": 1, "column_index": 3},
    ).json()
    bottle_id = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    ).json()["id"]

    stale_from = client.post(
        "/api/inventory-transactions",
        json={
            "bottle_id": bottle_id,
            "transaction_type": "MOVE",
            "from_location_id": location2["id"],
            "to_location_id": location3["id"],
        },
    )
    assert stale_from.status_code == 409
    assert "from_location_id" in stale_from.json()["detail"]

    same_target = client.post(
        "/api/inventory-transactions",
        json={
            "bottle_id": bottle_id,
            "transaction_type": "MOVE",
            "from_location_id": ids["location_id"],
            "to_location_id": ids["location_id"],
        },
    )
    assert same_target.status_code == 422


@pytest.mark.parametrize("transaction_type", ["CONSUME", "GIFT", "DAMAGE"])
def test_duplicate_outbound_transactions_are_rejected(client: TestClient, transaction_type: str) -> None:
    ids = create_minimum_inventory(client)
    location2 = client.post(
        "/api/locations",
        json={"cellar_id": ids["cellar_id"], "code": f"{transaction_type}-TARGET", "row_index": 2, "column_index": 2},
    )
    assert location2.status_code == 201
    bottle_id = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    ).json()["id"]

    first = client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": transaction_type, "note": "第一次出库"},
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": transaction_type, "note": "重复出库"},
    )
    assert duplicate.status_code == 409
    assert "already unavailable" in duplicate.json()["detail"]

    move_after_outbound = client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": "MOVE", "to_location_id": location2.json()["id"]},
    )
    assert move_after_outbound.status_code == 409
    assert "Only in-stock bottles can move" in move_after_outbound.json()["detail"]


def test_adjust_requires_note_and_keeps_audit_trail(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    bottle_id = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    ).json()["id"]

    missing_note = client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": "ADJUST", "from_location_id": ids["location_id"]},
    )
    assert missing_note.status_code == 422

    adjusted = client.post(
        "/api/inventory-transactions",
        json={
            "bottle_id": bottle_id,
            "transaction_type": "ADJUST",
            "from_location_id": ids["location_id"],
            "note": "盘点未找到，标记盘亏",
        },
    )
    assert adjusted.status_code == 201
    assert client.get(f"/api/bottles/{bottle_id}").json()["current_status"] == "lost"

    timeline = client.get(f"/api/bottles/{bottle_id}/transactions")
    assert [item["transaction_type"] for item in timeline.json()] == ["IN", "ADJUST"]
    assert timeline.json()[1]["note"] == "盘点未找到，标记盘亏"


def test_bottle_transaction_timeline_is_chronological(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    location2 = client.post(
        "/api/locations",
        json={"cellar_id": ids["cellar_id"], "code": "A-01-02", "row_index": 1, "column_index": 2},
    ).json()
    bottle_id = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    ).json()["id"]
    client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": "MOVE", "to_location_id": location2["id"]},
    )
    client.post(
        "/api/inventory-transactions",
        json={"bottle_id": bottle_id, "transaction_type": "GIFT", "note": "礼赠"},
    )

    timeline = client.get(f"/api/bottles/{bottle_id}/transactions")

    assert timeline.status_code == 200
    assert [item["transaction_type"] for item in timeline.json()] == ["IN", "MOVE", "GIFT"]


def test_direct_bottle_patch_cannot_mutate_stock_snapshot(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    bottle = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    ).json()

    response = client.patch(
        f"/api/bottles/{bottle['id']}",
        json={"current_status": "drunk", "personal_notes": "只允许更新非库存字段"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["current_status"] == "in_stock"
    assert body["personal_notes"] == "只允许更新非库存字段"


def test_dashboard_summary_uses_real_data(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    client.post("/api/bottles", json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]})

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["total_bottles"] == 1
    assert body["in_stock_bottles"] == 1
    assert body["recent_transactions"][0]["transaction_type"] == "IN"
    assert body["drink_window_summary"]["UNKNOWN"] == 1
    assert body["cellar_health_score"]["factors"]


def test_location_capacity_rejects_overfilled_add_and_move(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    location2 = client.post(
        "/api/locations",
        json={"cellar_id": ids["cellar_id"], "code": "A-01-02", "row_index": 1, "column_index": 2},
    )
    assert location2.status_code == 201

    bottle1 = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    )
    assert bottle1.status_code == 201

    duplicate_add = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": ids["location_id"]},
    )
    assert duplicate_add.status_code == 409
    assert "is full" in duplicate_add.json()["detail"]

    bottle2 = client.post(
        "/api/bottles",
        json={"vintage_id": ids["vintage_id"], "current_location_id": location2.json()["id"]},
    )
    assert bottle2.status_code == 201

    overfilled_move = client.post(
        "/api/inventory-transactions",
        json={
            "bottle_id": bottle1.json()["id"],
            "transaction_type": "MOVE",
            "to_location_id": location2.json()["id"],
        },
    )
    assert overfilled_move.status_code == 409
    assert "is full" in overfilled_move.json()["detail"]


def test_batch_create_cellar_locations_is_idempotent(client: TestClient) -> None:
    cellar = client.post("/api/cellars", json={"name": "批量柜", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    cellar_id = cellar.json()["id"]

    batch = client.post(
        f"/api/cellars/{cellar_id}/locations/batch",
        json={"rows": 2, "columns": 3, "code_prefix": "B", "capacity": 2},
    )
    assert batch.status_code == 201
    assert len(batch.json()) == 6
    assert {item["code"] for item in batch.json()} == {
        "B-01-01",
        "B-01-02",
        "B-01-03",
        "B-02-01",
        "B-02-02",
        "B-02-03",
    }
    assert all(item["capacity"] == 2 for item in batch.json())

    repeated = client.post(
        f"/api/cellars/{cellar_id}/locations/batch",
        json={"rows": 2, "columns": 3, "code_prefix": "B", "capacity": 2},
    )
    assert repeated.status_code == 201
    assert len(repeated.json()) == 6

    updated_cellar = client.get(f"/api/cellars/{cellar_id}")
    assert updated_cellar.json()["rows"] == 2
    assert updated_cellar.json()["columns"] == 3


def test_dashboard_summary_includes_drink_window_and_occupancy(client: TestClient) -> None:
    producer = client.post("/api/producers", json={"name_original": "Country Estate", "country": "France"})
    assert producer.status_code == 201
    wine = client.post(
        "/api/wines",
        json={
            "producer_id": producer.json()["id"],
            "name_original": "Cellar Red",
            "type": "red",
            "country": "France",
        },
    )
    assert wine.status_code == 201
    current_year = date.today().year
    vintage = client.post(
        "/api/vintages",
        json={
            "wine_id": wine.json()["id"],
            "vintage_year": 2020,
            "default_drink_from": current_year - 1,
            "default_drink_to": current_year + 1,
            "drink_window_confidence": "low",
        },
    )
    assert vintage.status_code == 201
    cellar = client.post("/api/cellars", json={"name": "洞察柜", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    locations = client.post(
        f"/api/cellars/{cellar.json()['id']}/locations/batch",
        json={"rows": 1, "columns": 2, "code_prefix": "I", "capacity": 1},
    )
    assert locations.status_code == 201
    bottle = client.post(
        "/api/bottles",
        json={"vintage_id": vintage.json()["id"], "current_location_id": locations.json()[0]["id"]},
    )
    assert bottle.status_code == 201
    assert bottle.json()["drink_window_status"] == "IN_WINDOW"

    response = client.get("/api/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["drink_window_counts"]["entering"] == 1
    assert body["drink_window_summary"]["IN_WINDOW"] == 1
    assert body["available_bottles"] == 1
    assert body["unavailable_bottles"] == 0
    assert body["upcoming_drink_candidates"][0]["bottle_id"] == bottle.json()["id"]
    assert body["upcoming_drink_candidates"][0]["drink_window_status"] == "IN_WINDOW"
    assert body["past_window_risks"] == []
    assert 0 <= body["cellar_health_score"]["score"] <= 100
    assert body["inventory_by_country"] == {"France": 1}
    assert body["inventory_by_type"] == {"red": 1}
    assert body["cellar_occupancy"] == [
        {
            "cellar_id": cellar.json()["id"],
            "name": "洞察柜",
            "capacity": 2,
            "occupied": 1,
            "empty": 1,
        }
    ]


def test_export_bottles_csv_contains_inventory_fields(client: TestClient) -> None:
    ids = create_minimum_inventory(client)
    bottle = client.post(
        "/api/bottles",
        json={
            "vintage_id": ids["vintage_id"],
            "current_location_id": ids["location_id"],
            "acquisition_date": "2026-06-13",
            "purchase_price": "288.00",
            "purchase_currency": "CNY",
            "purchase_source": "线下酒商",
            "personal_notes": "CSV 导出测试",
        },
    )
    assert bottle.status_code == 201

    response = client.get("/api/export/bottles.csv")

    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    content = response.content.decode("utf-8-sig")
    lines = content.splitlines()
    assert lines[0].startswith("bottle_id,producer,producer_cn,wine,wine_cn")
    assert "Chateau Test" in lines[1]
    assert "Grand Vin" in lines[1]
    assert "A-01-01" in lines[1]
    assert "288.00" in lines[1]
    assert "线下酒商" in lines[1]
