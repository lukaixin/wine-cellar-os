from __future__ import annotations

import io
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import create_app_engine, get_session
from app.main import app
from app.models import Base, Producer
from app.services.registry_service import (
    RegistryService,
    build_wine_identity_key,
    normalize_registry_text,
)
from app.services.winelist_import_service import EXPECTED_HEADERS


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_app_engine(f"sqlite:///{tmp_path / 'registry-foundation-test.db'}")
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


def test_canonical_key_normalizes_unicode_accents_spaces_and_punctuation() -> None:
    assert normalize_registry_text("  Château\u3000d’Yquem – Sautérnes  ") == "chateau d yquem sauternes"
    identity = build_wine_identity_key(
        "domaine de la romanee conti",
        "La Tâche",
        country="France",
        region="Bourgogne",
        appellation="Vosne-Romanée",
        wine_type="red",
    )
    assert identity == "domaine de la romanee conti | la tache | france | bourgogne | vosne romanee | red"
    assert identity != normalize_registry_text("La Tâche")


def test_alias_conflict_creates_review_queue_without_merging(client: TestClient, session_factory) -> None:
    response_a = client.post("/api/producers", json={"name_original": "Estate Alpha"})
    response_b = client.post("/api/producers", json={"name_original": "Estate Beta"})
    assert response_a.status_code == 201
    assert response_b.status_code == 201

    with session_factory() as session:
        registry = RegistryService(session)
        producer_a = session.get(Producer, response_a.json()["id"])
        producer_b = session.get(Producer, response_b.json()["id"])
        assert producer_a is not None
        assert producer_b is not None
        registry.record_alias(entity_type="producer", entity_id=producer_a.id, alias_text="Shared Alias", status="approved")
        conflict_alias = registry.record_alias(
            entity_type="producer",
            entity_id=producer_b.id,
            alias_text="Shared Alias",
            status="approved",
        )
        session.commit()
        assert conflict_alias.status == "conflict"

    aliases = client.get("/registry/aliases").json()
    queue = client.get("/registry/review-queue").json()
    assert {alias["status"] for alias in aliases} == {"conflict", "approved"}
    assert any(item["review_type"] == "alias_conflict" for item in queue)
    assert response_a.json()["merged_into_id"] is None
    assert response_b.json()["merged_into_id"] is None


def test_registry_quality_findings_report_duplicates_and_missing_fields(client: TestClient) -> None:
    producer_a = client.post("/api/producers", json={"name_original": "Duplicate Estate"}).json()
    producer_b = client.post("/api/producers", json={"name_original": "  duplicate-estate "}).json()
    wine = client.post(
        "/api/wines",
        json={
            "producer_id": producer_a["id"],
            "name_original": "Registry Red",
            "country": "France",
            "region": "Bordeaux",
            "type": "red",
        },
    ).json()
    vintage = client.post("/api/vintages", json={"wine_id": wine["id"], "vintage_year": 2020}).json()

    findings = client.get("/registry/quality/findings").json()
    finding_types = {finding["finding_type"] for finding in findings}
    assert producer_a["canonical_key"] == "duplicate estate"
    assert producer_b["canonical_key"] == "duplicate estate"
    assert "duplicate_producer" in finding_types
    assert "missing_drink_window" in finding_types
    assert any(finding["entity_id"] == vintage["id"] for finding in findings)
    queue = client.get("/registry/review-queue").json()
    assert any(item["review_type"] == "suspected_duplicate" for item in queue)


def test_winelist_draft_outputs_scores_and_import_mappings(client: TestClient) -> None:
    producer = client.post(
        "/api/producers",
        json={"name_original": "Chateau Margaux", "country": "France", "region": "Bordeaux"},
    ).json()
    wine = client.post(
        "/api/wines",
        json={
            "producer_id": producer["id"],
            "name_original": "Grand Vin",
            "country": "France",
            "region": "Bordeaux",
            "appellation": "Margaux",
            "type": "red",
        },
    ).json()
    client.post("/api/vintages", json={"wine_id": wine["id"], "vintage_year": 2019})

    response = client.post(
        "/api/import/winelist/draft",
        files={
            "file": (
                "RegistryWineList.xlsx",
                _workbook_bytes(
                    {
                        "No": 1,
                        "Country": "France",
                        "Region": "Bordeaux",
                        "Sub-Region": "Margaux",
                        "Producer": "Château Margaux",
                        "Wine": "Grand Vin",
                        "Style": "red",
                        "Vintage": 2019,
                        "Quantity": 1,
                        "Cost": 1000,
                        "Channel": "manual",
                        "WS Price": None,
                        "Status": None,
                        "Total": None,
                        "CAVE": "C",
                    }
                ),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    row = response.json()["rows"][0]["normalized"]
    assert row["producer_match_score"] == 100
    assert row["wine_match_score"] == 100
    assert row["vintage_match_score"] == 100
    assert row["overall_match_score"] == 100
    assert row["decision"] == "auto_accepted"

    mappings = client.get("/registry/import-mappings").json()
    assert len(mappings) == 3
    assert {mapping["target_entity_type"] for mapping in mappings} == {"producer", "wine", "vintage"}
    assert {mapping["decision"] for mapping in mappings} == {"auto_accepted"}
    assert {mapping["match_score"] for mapping in mappings} == {100}


def test_registry_search_supports_canonical_alias_chinese_and_fuzzy_matches(
    client: TestClient,
    session_factory,
) -> None:
    canonical = client.post("/api/producers", json={"name_original": "DRC"}).json()
    producer = client.post(
        "/api/producers",
        json={
            "name_original": "Domaine de la Romanee-Conti",
            "name_cn": "罗曼尼康帝",
            "country": "France",
            "region": "Bourgogne",
        },
    ).json()
    wine = client.post(
        "/api/wines",
        json={
            "producer_id": producer["id"],
            "name_original": "Romanee-Conti Grand Cru",
            "name_cn": "罗曼尼康帝特级园",
            "country": "France",
            "region": "Bourgogne",
            "type": "red",
        },
    ).json()
    vintage = client.post(
        "/api/vintages",
        json={
            "wine_id": wine["id"],
            "vintage_year": 2020,
            "default_drink_from": 2030,
            "default_drink_to": 2050,
            "drink_window_confidence": "low",
        },
    ).json()

    with session_factory() as session:
        registry = RegistryService(session)
        registry.record_alias(
            entity_type="producer",
            entity_id=producer["id"],
            alias_text="DRC",
            status="approved",
            source="manual",
        )
        registry.record_alias(
            entity_type="wine",
            entity_id=wine["id"],
            alias_text="Romanee Conti",
            status="approved",
            source="manual",
        )
        session.commit()

    drc = client.get("/registry/search?q=drc").json()
    assert drc["producers"][0]["id"] == canonical["id"]
    assert drc["producers"][0]["matched_by"] == "canonical_name"
    assert any(item["id"] == producer["id"] and item["matched_by"] == "alias" for item in drc["producers"])
    assert any(item["id"] == wine["id"] and item["matched_by"] == "alias" for item in drc["wines"])

    chinese = client.get("/registry/search?q=罗曼尼康帝").json()
    assert chinese["producers"][0]["matched_by"] == "chinese_name"
    assert chinese["wines"][0]["matched_by"] == "chinese_name"

    fuzzy = client.get("/registry/search?q=romanee conty").json()
    assert fuzzy["wines"][0]["id"] == wine["id"]
    assert fuzzy["wines"][0]["matched_by"] == "fuzzy"
    assert any(item["id"] == vintage["id"] for item in fuzzy["vintages"])


def test_registry_search_returns_partial_matches_for_common_discovery_queries(client: TestClient) -> None:
    client.post(
        "/api/producers",
        json={"name_original": "Chateau Rayas", "country": "France", "region": "Southern Rhone"},
    )
    client.post(
        "/api/producers",
        json={"name_original": "Valentini", "country": "Italy", "region": "Abruzzo"},
    )

    rayas = client.get("/registry/search?q=rayas")
    valentini = client.get("/api/registry/search?q=valentini")

    assert rayas.status_code == 200
    assert rayas.json()["producers"][0]["display_name"] == "Chateau Rayas"
    assert rayas.json()["producers"][0]["matched_by"] == "partial"
    assert valentini.status_code == 200
    assert valentini.json()["producers"][0]["matched_by"] == "canonical_name"


def test_registry_detail_apis_return_read_only_aggregates(client: TestClient, session_factory) -> None:
    producer = client.post(
        "/api/producers",
        json={"name_original": "Detail Estate", "name_cn": "详情酒庄", "country": "France", "region": "Bordeaux"},
    ).json()
    wine = client.post(
        "/api/wines",
        json={"producer_id": producer["id"], "name_original": "Detail Red", "country": "France", "region": "Bordeaux"},
    ).json()
    vintage = client.post(
        "/api/vintages",
        json={
            "wine_id": wine["id"],
            "vintage_year": 2018,
            "default_drink_from": 2025,
            "default_drink_to": 2035,
            "drink_window_confidence": "medium",
        },
    ).json()

    with session_factory() as session:
        registry = RegistryService(session)
        registry.record_alias(entity_type="producer", entity_id=producer["id"], alias_text="Detail Alias", status="approved")
        registry.record_alias(entity_type="wine", entity_id=wine["id"], alias_text="Detail Rouge", status="candidate")
        session.commit()

    producer_detail = client.get(f"/registry/producers/{producer['id']}").json()
    wine_detail = client.get(f"/registry/wines/{wine['id']}").json()
    vintage_detail = client.get(f"/registry/vintages/{vintage['id']}").json()

    assert producer_detail["canonical_name"] == "Detail Estate"
    assert producer_detail["aliases"] == ["Detail Alias"]
    assert producer_detail["wine_count"] == 1
    assert wine_detail["producer_name"] == "Detail Estate"
    assert wine_detail["aliases"] == ["Detail Rouge"]
    assert wine_detail["vintage_count"] == 1
    assert vintage_detail["producer_name"] == "Detail Estate"
    assert vintage_detail["wine_name"] == "Detail Red"
    assert vintage_detail["bottle_count"] == 0
    assert vintage_detail["default_drink_from"] == 2025


def test_registry_discovery_surfaces_recent_entities_and_quality_risks(client: TestClient) -> None:
    producer_a = client.post("/api/producers", json={"name_original": "Duplicate Discovery"}).json()
    client.post("/api/producers", json={"name_original": "duplicate-discovery"}).json()
    wine = client.post("/api/wines", json={"producer_id": producer_a["id"], "name_original": "Discovery Red"}).json()
    client.post("/api/vintages", json={"wine_id": wine["id"], "vintage_year": 2021})

    response = client.get("/registry/discovery")

    assert response.status_code == 200
    body = response.json()
    assert body["recent_producers"]
    assert body["recent_wines"]
    assert body["recent_vintages"]
    assert any(risk["finding_type"] == "duplicate_producer" for risk in body["quality_risks"])


def _workbook_bytes(row: dict[str, object]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Stock"
    sheet.append(EXPECTED_HEADERS)
    sheet.append([row.get(header) for header in EXPECTED_HEADERS])
    stream = io.BytesIO()
    workbook.save(stream)
    return stream.getvalue()
