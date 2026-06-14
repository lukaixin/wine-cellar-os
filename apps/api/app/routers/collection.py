from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.common import CollectionBottleDetail, CollectionBottleTimelineEvent, CollectionSearchResponse
from app.services.collection_service import CollectionSearchFilters, CollectionService

router = APIRouter(prefix="/collection", tags=["collection"])
api_router = APIRouter(prefix="/api/collection", tags=["collection"])


def _search_collection(
    q: str | None = Query(default=None, min_length=1, max_length=120),
    producer_id: str | None = None,
    producer: str | None = Query(default=None, min_length=1, max_length=120),
    vintage_year: int | None = Query(default=None, ge=0, le=9999),
    location_id: str | None = None,
    location: str | None = Query(default=None, min_length=1, max_length=120),
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict:
    return CollectionService(session).search(
        CollectionSearchFilters(
            query=q,
            producer_id=producer_id,
            producer=producer,
            vintage_year=vintage_year,
            location_id=location_id,
            location=location,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
    )


def _get_collection_bottle(bottle_id: str, session: Session = Depends(get_session)) -> dict:
    detail = CollectionService(session).bottle_detail(bottle_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bottle not found")
    return detail


def _get_collection_bottle_timeline(bottle_id: str, session: Session = Depends(get_session)) -> list[dict]:
    timeline = CollectionService(session).bottle_timeline(bottle_id)
    if timeline is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bottle not found")
    return timeline


router.get("/search", response_model=CollectionSearchResponse)(_search_collection)
router.get("/bottles/{bottle_id}", response_model=CollectionBottleDetail)(_get_collection_bottle)
router.get("/bottles/{bottle_id}/timeline", response_model=list[CollectionBottleTimelineEvent])(
    _get_collection_bottle_timeline
)

api_router.get("/search", response_model=CollectionSearchResponse)(_search_collection)
api_router.get("/bottles/{bottle_id}", response_model=CollectionBottleDetail)(_get_collection_bottle)
api_router.get("/bottles/{bottle_id}/timeline", response_model=list[CollectionBottleTimelineEvent])(
    _get_collection_bottle_timeline
)
