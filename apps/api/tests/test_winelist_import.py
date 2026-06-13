from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base
from app.services.winelist_import_service import WineListImportService

SAMPLE_WINELIST = Path(__file__).resolve().parents[3] / "data" / "sample" / "WineList.xlsx"


@pytest.fixture()
def client(tmp_path) -> Generator[TestClient, None, None]:
    engine = create_app_engine(f"sqlite:///{tmp_path / 'winelist-import-test.db'}")
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


def draft_sample(client: TestClient):
    assert SAMPLE_WINELIST.exists()
    with SAMPLE_WINELIST.open("rb") as handle:
        return client.post(
            "/api/import/winelist/draft",
            files={
                "file": (
                    "WineList.xlsx",
                    handle.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )


def test_winelist_draft_validates_stock_without_mutating_inventory(client: TestClient) -> None:
    response = draft_sample(client)

    assert response.status_code == 200
    body = response.json()
    assert body["sheet_name"] == "Stock"
    assert body["total_rows"] == 114
    assert body["valid_rows"] == 114
    assert body["invalid_rows"] == 0
    assert body["bottle_count"] == 119
    assert body["location_counts"] == {
        "法国朋友家 / FR": 3,
        "家中酒柜 / C": 86,
        "家中散放 / HOME-OUTSIDE": 30,
    }
    assert body["registry_preview"]["producers_new"] > 0
    assert any("Southern Rhone" in warning for warning in body["warnings"])
    assert client.get("/api/producers").json() == []
    assert client.get("/api/wines").json() == []
    assert client.get("/api/vintages").json() == []
    assert client.get("/api/bottles").json() == []
    assert client.get("/api/inventory-transactions").json() == []

    batches = client.get("/imports/batches?limit=10&offset=0")
    assert batches.status_code == 200
    batch_item = batches.json()["items"][0]
    assert batches.json()["total"] == 1
    assert batch_item["id"] == body["batch_id"]
    assert batch_item["filename"] == "WineList.xlsx"
    assert batch_item["status"] == "draft"
    assert batch_item["total_rows"] == 114
    assert batch_item["success_rows"] == 114
    assert batch_item["warning_rows"] > 0
    assert batch_item["error_rows"] == 0
    assert batch_item["created_bottle_count"] == 0

    detail = client.get(f"/imports/batches/{body['batch_id']}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["filename"] == "WineList.xlsx"
    assert detail_body["sheet_name"] == "Stock"
    assert detail_body["total_rows"] == 114
    assert len(detail_body["rows"]) == 114
    first_row = detail_body["rows"][0]
    assert first_row["row_number"] == 2
    assert first_row["raw_values"]["Producer"]
    assert first_row["parsed_producer"]
    assert first_row["parsed_wine"]
    assert isinstance(first_row["parsed_vintage"], int)
    assert first_row["quantity"] >= 1
    assert first_row["created_bottle_ids"] == []
    assert first_row["ledger_transaction_ids"] == []


def test_winelist_confirm_expands_quantity_and_creates_in_ledger(client: TestClient) -> None:
    draft = draft_sample(client)
    assert draft.status_code == 200
    batch_id = draft.json()["batch_id"]

    confirm = client.post(f"/api/import/winelist/{batch_id}/confirm")

    assert confirm.status_code == 201
    body = confirm.json()
    assert body["created_bottles"] == 119
    assert len(body["created_bottle_ids"]) == 119
    assert len(body["created_transaction_ids"]) == 119
    assert body["transaction_type"] == "IN"

    bottles = client.get("/api/bottles").json()
    transactions = client.get("/api/inventory-transactions").json()
    assert len(bottles) == 119
    assert len(transactions) == 119
    assert {transaction["transaction_type"] for transaction in transactions} == {"IN"}
    assert {transaction["actor"] for transaction in transactions} == {"winelist_import"}
    assert {bottle["current_status"] for bottle in bottles} == {"in_stock"}

    location_counts = {}
    for bottle in bottles:
        key = f"{bottle['cellar_name']} / {bottle['location_code']}"
        location_counts[key] = location_counts.get(key, 0) + 1
    assert location_counts == {
        "法国朋友家 / FR": 3,
        "家中酒柜 / C": 86,
        "家中散放 / HOME-OUTSIDE": 30,
    }

    detail = client.get(f"/api/imports/batches/{batch_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["status"] == "confirmed"
    assert detail_body["success_rows"] == 114
    assert detail_body["created_bottle_count"] == 119
    assert detail_body["error_rows"] == 0
    assert detail_body["confirmed_at"] is not None
    assert sum(len(row["created_bottle_ids"]) for row in detail_body["rows"]) == 119
    assert sum(len(row["ledger_transaction_ids"]) for row in detail_body["rows"]) == 119


def test_winelist_draft_rejects_rows_already_confirmed(client: TestClient) -> None:
    draft = draft_sample(client)
    assert draft.status_code == 200
    confirm = client.post(f"/api/import/winelist/{draft.json()['batch_id']}/confirm")
    assert confirm.status_code == 201

    duplicate_draft = draft_sample(client)

    assert duplicate_draft.status_code == 200
    body = duplicate_draft.json()
    assert body["valid_rows"] == 0
    assert body["invalid_rows"] == 114
    assert body["bottle_count"] == 0
    assert any("already confirmed" in error for row in body["rows"] for error in row["errors"])

    batches = client.get("/imports/batches?limit=1&offset=1")
    assert batches.status_code == 200
    assert batches.json()["total"] == 2
    assert len(batches.json()["items"]) == 1
    assert batches.json()["limit"] == 1
    assert batches.json()["offset"] == 1


def test_winelist_confirm_rolls_back_whole_batch_on_mid_batch_failure(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draft = draft_sample(client)
    assert draft.status_code == 200
    batch_id = draft.json()["batch_id"]
    original_create = WineListImportService._create_imported_bottle
    calls = 0

    def fail_after_first(self, row, location, batch, db_row, bottle_index):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("forced WineList failure")
        return original_create(self, row, location, batch, db_row, bottle_index)

    monkeypatch.setattr(WineListImportService, "_create_imported_bottle", fail_after_first)

    response = client.post(f"/api/import/winelist/{batch_id}/confirm")

    assert response.status_code == 500
    assert "rolled back" in response.json()["detail"]
    assert calls == 2
    assert client.get("/api/bottles").json() == []
    assert client.get("/api/inventory-transactions").json() == []
    assert client.get("/api/producers").json() == []
