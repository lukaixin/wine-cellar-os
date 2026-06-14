from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import ImportMapping, RegistryAlias, RegistryQualityFinding, RegistryReviewQueue
from app.schemas.common import (
    ImportMappingRead,
    RegistryAliasRead,
    RegistryDiscoveryResponse,
    RegistryProducerDetail,
    RegistryQualityFindingRead,
    RegistryReviewQueueRead,
    RegistrySearchResponse,
    RegistryVintageDetail,
    RegistryWineDetail,
)
from app.services.registry_service import RegistryService

router = APIRouter(prefix="/registry", tags=["registry"])
api_router = APIRouter(prefix="/api/registry", tags=["registry"])


def _list_aliases(
    limit: int = Query(default=100, ge=1, le=500),
    session: Session = Depends(get_session),
) -> list[RegistryAlias]:
    return list(
        session.scalars(
            select(RegistryAlias)
            .order_by(RegistryAlias.updated_at.desc(), RegistryAlias.created_at.desc())
            .limit(limit)
        )
    )


def _list_import_mappings(
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> list[ImportMapping]:
    return list(
        session.scalars(
            select(ImportMapping)
            .order_by(ImportMapping.created_at.desc(), ImportMapping.source_row_number.asc())
            .limit(limit)
        )
    )


def _list_review_queue(
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> list[RegistryReviewQueue]:
    return list(
        session.scalars(
            select(RegistryReviewQueue)
            .order_by(RegistryReviewQueue.created_at.desc(), RegistryReviewQueue.id.desc())
            .limit(limit)
        )
    )


def _list_quality_findings(
    limit: int = Query(default=200, ge=1, le=1000),
    session: Session = Depends(get_session),
) -> list[RegistryQualityFinding]:
    registry = RegistryService(session)
    registry.ensure_quality_findings()
    session.commit()
    return list(
        session.scalars(
            select(RegistryQualityFinding)
            .order_by(RegistryQualityFinding.created_at.desc(), RegistryQualityFinding.id.desc())
            .limit(limit)
        )
    )


def _search_registry(
    q: str = Query(min_length=1, max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    return RegistryService(session).search(q, limit_per_type=limit)


def _get_registry_producer(producer_id: str, session: Session = Depends(get_session)) -> dict:
    detail = RegistryService(session).producer_detail(producer_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producer not found")
    return detail


def _get_registry_wine(wine_id: str, session: Session = Depends(get_session)) -> dict:
    detail = RegistryService(session).wine_detail(wine_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wine not found")
    return detail


def _get_registry_vintage(vintage_id: str, session: Session = Depends(get_session)) -> dict:
    detail = RegistryService(session).vintage_detail(vintage_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vintage not found")
    return detail


def _get_registry_discovery(
    limit: int = Query(default=5, ge=1, le=20),
    risk_limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
) -> dict:
    registry = RegistryService(session)
    discovery = registry.discovery(limit_per_type=limit, risk_limit=risk_limit)
    session.commit()
    return discovery


router.get("/search", response_model=RegistrySearchResponse)(_search_registry)
router.get("/discovery", response_model=RegistryDiscoveryResponse)(_get_registry_discovery)
router.get("/producers/{producer_id}", response_model=RegistryProducerDetail)(_get_registry_producer)
router.get("/wines/{wine_id}", response_model=RegistryWineDetail)(_get_registry_wine)
router.get("/vintages/{vintage_id}", response_model=RegistryVintageDetail)(_get_registry_vintage)
router.get("/aliases", response_model=list[RegistryAliasRead])(_list_aliases)
router.get("/import-mappings", response_model=list[ImportMappingRead])(_list_import_mappings)
router.get("/review-queue", response_model=list[RegistryReviewQueueRead])(_list_review_queue)
router.get("/quality/findings", response_model=list[RegistryQualityFindingRead])(_list_quality_findings)

api_router.get("/search", response_model=RegistrySearchResponse)(_search_registry)
api_router.get("/discovery", response_model=RegistryDiscoveryResponse)(_get_registry_discovery)
api_router.get("/producers/{producer_id}", response_model=RegistryProducerDetail)(_get_registry_producer)
api_router.get("/wines/{wine_id}", response_model=RegistryWineDetail)(_get_registry_wine)
api_router.get("/vintages/{vintage_id}", response_model=RegistryVintageDetail)(_get_registry_vintage)
api_router.get("/aliases", response_model=list[RegistryAliasRead])(_list_aliases)
api_router.get("/import-mappings", response_model=list[ImportMappingRead])(_list_import_mappings)
api_router.get("/review-queue", response_model=list[RegistryReviewQueueRead])(_list_review_queue)
api_router.get("/quality/findings", response_model=list[RegistryQualityFindingRead])(_list_quality_findings)
