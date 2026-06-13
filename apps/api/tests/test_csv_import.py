from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_app_engine(f"sqlite:///{tmp_path / 'csv-import-test.db'}")
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


def test_csv_import_draft_validates_rows_without_mutating_inventory(client: TestClient) -> None:
    cellar = client.post("/api/cellars", json={"name": "Import Cellar", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    location = client.post(
        "/api/locations",
        json={"cellar_id": cellar.json()["id"], "code": "I-01-01", "row_index": 1, "column_index": 1, "capacity": 2},
    )
    assert location.status_code == 201
    csv_text = "\n".join(
        [
            "producer_name,wine_name,vintage_year,bottle_size_ml,cellar_name,location_code,country,region,type,purchase_price,purchase_currency,purchase_date,purchase_source,drink_from,drink_to,notes,tags",
            "Import Estate,Import Red,2020,750,Import Cellar,I-01-01,France,Bordeaux,red,288.00,CNY,2026-06-13,Merchant,2025,2028,first row,tag-a;tag-b",
            "Broken Estate,,bad-year,750,Import Cellar,MISSING,,,,,,,,,,",
        ]
    )

    response = client.post("/api/import/csv/draft", json={"filename": "import.csv", "csv_text": csv_text})

    assert response.status_code == 200
    body = response.json()
    assert body["total_rows"] == 2
    assert body["valid_rows"] == 1
    assert body["invalid_rows"] == 1
    assert body["rows"][0]["status"] == "valid"
    assert body["rows"][0]["normalized"]["producer_name"] == "Import Estate"
    assert body["rows"][0]["warnings"]
    assert body["rows"][1]["status"] == "invalid"
    assert any("wine_name" in error for error in body["rows"][1]["errors"])
    assert client.get("/api/bottles").json() == []
    assert client.get("/api/inventory-transactions").json() == []


def test_csv_import_confirm_creates_bottle_through_in_ledger(client: TestClient) -> None:
    cellar = client.post("/api/cellars", json={"name": "Confirm Cellar", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    location = client.post(
        "/api/locations",
        json={"cellar_id": cellar.json()["id"], "code": "C-01-01", "row_index": 1, "column_index": 1, "capacity": 1},
    )
    assert location.status_code == 201
    csv_text = "\n".join(
        [
            "producer_name,wine_name,vintage_year,bottle_size_ml,cellar_name,location_code,country,region,type,purchase_price,purchase_currency,purchase_date,purchase_source,drink_from,drink_to,notes",
            "Confirm Estate,Confirm Red,2019,750,Confirm Cellar,C-01-01,France,Burgundy,red,388.00,CNY,2026-06-13,Importer,2024,2030,confirmed row",
        ]
    )
    draft = client.post("/api/import/csv/draft", json={"filename": "confirm.csv", "csv_text": csv_text})
    assert draft.status_code == 200
    assert draft.json()["valid_rows"] == 1

    confirm = client.post("/api/import/csv/confirm", json={"rows": [draft.json()["rows"][0]["normalized"]]})

    assert confirm.status_code == 201
    body = confirm.json()
    assert body["created_bottles"] == 1
    bottle_id = body["created_bottle_ids"][0]
    bottle = client.get(f"/api/bottles/{bottle_id}")
    assert bottle.status_code == 200
    bottle_body = bottle.json()
    assert bottle_body["producer_name"] == "Confirm Estate"
    assert bottle_body["wine_name"] == "Confirm Red"
    assert bottle_body["location_code"] == "C-01-01"
    assert bottle_body["current_status"] == "in_stock"
    timeline = client.get(f"/api/bottles/{bottle_id}/transactions")
    assert timeline.status_code == 200
    assert [item["transaction_type"] for item in timeline.json()] == ["IN"]
    assert timeline.json()[0]["actor"] == "csv_import"


def test_csv_import_confirm_rejects_batch_over_capacity_without_creating_bottles(client: TestClient) -> None:
    cellar = client.post("/api/cellars", json={"name": "Capacity Cellar", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    location = client.post(
        "/api/locations",
        json={"cellar_id": cellar.json()["id"], "code": "K-01-01", "row_index": 1, "column_index": 1, "capacity": 1},
    )
    assert location.status_code == 201
    rows = [
        {
            "producer_name": "Capacity Estate",
            "wine_name": "Capacity Red",
            "vintage_year": 2020,
            "bottle_size_ml": 750,
            "cellar_name": "Capacity Cellar",
            "location_code": "K-01-01",
            "purchase_currency": "CNY",
            "tags": [],
        },
        {
            "producer_name": "Capacity Estate",
            "wine_name": "Capacity Red",
            "vintage_year": 2021,
            "bottle_size_ml": 750,
            "cellar_name": "Capacity Cellar",
            "location_code": "K-01-01",
            "purchase_currency": "CNY",
            "tags": [],
        },
    ]

    response = client.post("/api/import/csv/confirm", json={"rows": rows})

    assert response.status_code == 422
    assert "full for import" in response.json()["detail"]
    assert client.get("/api/bottles").json() == []
    assert client.get("/api/inventory-transactions").json() == []
