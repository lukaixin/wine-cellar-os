from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Vintage, Wine
from app.routers.helpers import apply_update, commit_or_400, get_or_404, vintage_to_read
from app.schemas.common import VintageCreate, VintageRead, VintageUpdate

router = APIRouter(prefix="/api/vintages", tags=["vintages"])


def _vintage_query():
    return select(Vintage).options(joinedload(Vintage.wine).joinedload(Wine.producer))


@router.get("", response_model=list[VintageRead])
def list_vintages(session: Session = Depends(get_session)) -> list[dict]:
    vintages = session.scalars(_vintage_query().order_by(Vintage.vintage_year.desc().nullslast())).all()
    return [vintage_to_read(vintage) for vintage in vintages]


@router.post("", response_model=VintageRead, status_code=201)
def create_vintage(payload: VintageCreate, session: Session = Depends(get_session)) -> dict:
    get_or_404(session, Wine, payload.wine_id, "Wine")
    vintage = Vintage(**payload.model_dump())
    session.add(vintage)
    commit_or_400(session)
    vintage = session.scalars(_vintage_query().where(Vintage.id == vintage.id)).one()
    return vintage_to_read(vintage)


@router.get("/{vintage_id}", response_model=VintageRead)
def get_vintage(vintage_id: str, session: Session = Depends(get_session)) -> dict:
    vintage = session.scalars(_vintage_query().where(Vintage.id == vintage_id)).first()
    if vintage is None:
        get_or_404(session, Vintage, vintage_id, "Vintage")
    return vintage_to_read(vintage)


@router.patch("/{vintage_id}", response_model=VintageRead)
def update_vintage(vintage_id: str, payload: VintageUpdate, session: Session = Depends(get_session)) -> dict:
    vintage = get_or_404(session, Vintage, vintage_id, "Vintage")
    values = payload.model_dump(exclude_unset=True)
    if "wine_id" in values:
        get_or_404(session, Wine, values["wine_id"], "Wine")
    apply_update(vintage, values)
    commit_or_400(session)
    vintage = session.scalars(_vintage_query().where(Vintage.id == vintage.id)).one()
    return vintage_to_read(vintage)
