from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.common import AnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])
api_router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _analytics_summary(
    recent_limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict:
    return AnalyticsService(session).summary(recent_limit=recent_limit)


router.get("/summary", response_model=AnalyticsSummary)(_analytics_summary)
api_router.get("/summary", response_model=AnalyticsSummary)(_analytics_summary)
