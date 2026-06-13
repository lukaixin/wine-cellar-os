from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base


@pytest.fixture()
def client(tmp_path, monkeypatch) -> Generator[TestClient, None, None]:
    monkeypatch.setenv("WINE_CELLAR_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("WINE_CELLAR_LABEL_UPLOAD_DIR", str(tmp_path / "data" / "uploads" / "labels"))
    monkeypatch.setenv("WINE_CELLAR_LABEL_MAX_UPLOAD_BYTES", str(1024 * 1024))
    engine = create_app_engine(f"sqlite:///{tmp_path / 'label-intake-test.db'}")
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


def create_location(client: TestClient) -> str:
    cellar = client.post("/api/cellars", json={"name": "Label Cellar", "cellar_type": "cabinet"})
    assert cellar.status_code == 201
    location = client.post(
        "/api/locations",
        json={"cellar_id": cellar.json()["id"], "code": "L-01-01", "row_index": 1, "column_index": 1, "capacity": 1},
    )
    assert location.status_code == 201
    return location.json()["id"]


def upload_label(client: TestClient, filename: str = "Label_Estate_Grand_Vin_2018_750ml.jpg"):
    return client.post(
        "/api/intake/label-images",
        files={"file": (filename, b"fake-jpeg-bytes", "image/jpeg")},
    )


def test_label_upload_stores_metadata_and_file(client: TestClient, tmp_path) -> None:
    response = upload_label(client)

    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "Label_Estate_Grand_Vin_2018_750ml.jpg"
    assert body["content_type"] == "image/jpeg"
    assert body["size_bytes"] == len(b"fake-jpeg-bytes")
    assert len(body["sha256"]) == 64
    assert body["stored_filename"] != body["original_filename"]
    assert body["file_path"].startswith("uploads/labels/")
    assert (tmp_path / "data" / body["file_path"]).exists()
    assert body["bottle_id"] is None


def test_label_upload_dir_defaults_inside_configured_data_dir(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("WINE_CELLAR_DATA_DIR", str(tmp_path / "custom-data"))
    monkeypatch.delenv("WINE_CELLAR_LABEL_UPLOAD_DIR", raising=False)

    settings = get_settings()

    assert settings.label_upload_dir == str(Path(settings.data_dir) / "uploads" / "labels")


def test_label_draft_uses_mock_recognizer_without_mutating_inventory(client: TestClient) -> None:
    upload = upload_label(client)
    assert upload.status_code == 201

    draft = client.post("/api/intake/label-drafts", json={"upload_id": upload.json()["id"]})

    assert draft.status_code == 200
    body = draft.json()
    assert body["recognizer"] == "mock-local-filename-heuristic"
    assert body["confidence"] == "low"
    assert body["candidate_fields"]["producer_name"] == "Label Estate"
    assert body["candidate_fields"]["wine_name"] == "Grand Vin"
    assert body["candidate_fields"]["vintage_year"] == 2018
    assert body["candidate_fields"]["bottle_size_ml"] == 750
    assert body["warnings"]
    assert client.get("/api/bottles").json() == []
    assert client.get("/api/inventory-transactions").json() == []


def test_label_confirm_creates_bottle_through_in_ledger_and_links_upload(client: TestClient) -> None:
    location_id = create_location(client)
    upload = upload_label(client)
    assert upload.status_code == 201
    draft = client.post("/api/intake/label-drafts", json={"upload_id": upload.json()["id"]})
    assert draft.status_code == 200
    fields = draft.json()["candidate_fields"]

    confirm = client.post(
        "/api/intake/label-drafts/confirm",
        json={
            "upload_id": upload.json()["id"],
            "producer_name": fields["producer_name"],
            "wine_name": fields["wine_name"],
            "vintage_year": fields["vintage_year"],
            "bottle_size_ml": fields["bottle_size_ml"],
            "location_id": location_id,
            "country": "France",
            "region": "Bordeaux",
            "type": "red",
            "notes": "confirmed from label draft",
        },
    )

    assert confirm.status_code == 201
    bottle_id = confirm.json()["bottle_id"]
    bottle = client.get(f"/api/bottles/{bottle_id}")
    assert bottle.status_code == 200
    bottle_body = bottle.json()
    assert bottle_body["producer_name"] == "Label Estate"
    assert bottle_body["wine_name"] == "Grand Vin"
    assert bottle_body["current_status"] == "in_stock"
    assert bottle_body["location_code"] == "L-01-01"
    timeline = client.get(f"/api/bottles/{bottle_id}/transactions")
    assert [item["transaction_type"] for item in timeline.json()] == ["IN"]
    assert timeline.json()[0]["actor"] == "label_intake"

    linked_draft = client.post("/api/intake/label-drafts", json={"upload_id": upload.json()["id"]})
    assert linked_draft.json()["upload"]["bottle_id"] == bottle_id


def test_label_upload_rejects_invalid_file_type(client: TestClient) -> None:
    response = client.post(
        "/api/intake/label-images",
        files={"file": ("label.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 415
    assert client.get("/api/bottles").json() == []


def test_label_upload_rejects_size_limit(client: TestClient, monkeypatch) -> None:
    monkeypatch.setenv("WINE_CELLAR_LABEL_MAX_UPLOAD_BYTES", "4")

    response = client.post(
        "/api/intake/label-images",
        files={"file": ("large.jpg", b"too large", "image/jpeg")},
    )

    assert response.status_code == 413
    assert client.get("/api/bottles").json() == []
