from fastapi import APIRouter, Depends
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Producer, Wine
from app.routers.helpers import apply_update, commit_or_400, get_or_404, wine_to_read
from app.schemas.common import WineCreate, WineRead, WineUpdate
from app.services.registry_service import RegistryService

router = APIRouter(prefix="/api/wines", tags=["wines"])


@router.get("", response_model=list[WineRead])
def list_wines(session: Session = Depends(get_session)) -> list[dict]:
    wines = session.scalars(select(Wine).options(joinedload(Wine.producer)).order_by(Wine.name_original)).all()
    return [wine_to_read(wine) for wine in wines]


@router.post("", response_model=WineRead, status_code=201)
def create_wine(payload: WineCreate, session: Session = Depends(get_session)) -> dict:
    producer = get_or_404(session, Producer, payload.producer_id, "Producer")
    wine = Wine(**payload.model_dump())
    RegistryService(session).apply_wine_fields(wine, producer)
    session.add(wine)
    commit_or_400(session)
    wine = session.scalars(
        select(Wine).options(joinedload(Wine.producer)).where(Wine.id == wine.id)
    ).one()
    return wine_to_read(wine)


@router.get("/search", response_model=list[WineRead])
def search_wines(q: str, session: Session = Depends(get_session)) -> list[dict]:
    query = f"%{q}%"
    wines = session.scalars(
        select(Wine)
        .options(joinedload(Wine.producer))
        .where(or_(Wine.name_original.ilike(query), Wine.name_cn.ilike(query)))
        .order_by(Wine.name_original)
    ).all()
    return [wine_to_read(wine) for wine in wines]


@router.get("/{wine_id}", response_model=WineRead)
def get_wine(wine_id: str, session: Session = Depends(get_session)) -> dict:
    wine = session.scalars(select(Wine).options(joinedload(Wine.producer)).where(Wine.id == wine_id)).first()
    if wine is None:
        get_or_404(session, Wine, wine_id, "Wine")
    return wine_to_read(wine)


@router.patch("/{wine_id}", response_model=WineRead)
def update_wine(wine_id: str, payload: WineUpdate, session: Session = Depends(get_session)) -> dict:
    wine = get_or_404(session, Wine, wine_id, "Wine")
    values = payload.model_dump(exclude_unset=True)
    if "producer_id" in values:
        get_or_404(session, Producer, values["producer_id"], "Producer")
    apply_update(wine, values)
    RegistryService(session).apply_wine_fields(wine)
    commit_or_400(session)
    wine = session.scalars(select(Wine).options(joinedload(Wine.producer)).where(Wine.id == wine.id)).one()
    return wine_to_read(wine)
