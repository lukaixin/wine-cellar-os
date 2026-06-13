from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Cellar, Location
from app.routers.helpers import apply_update, commit_or_400, get_or_404, location_to_read
from app.schemas.common import (
    CellarCreate,
    CellarLocationBatchCreate,
    CellarRead,
    CellarUpdate,
    LocationCreate,
    LocationRead,
)

router = APIRouter(prefix="/api/cellars", tags=["cellars"])


@router.get("", response_model=list[CellarRead])
def list_cellars(session: Session = Depends(get_session)) -> list[Cellar]:
    return list(session.scalars(select(Cellar).order_by(Cellar.name)))


@router.post("", response_model=CellarRead, status_code=201)
def create_cellar(payload: CellarCreate, session: Session = Depends(get_session)) -> Cellar:
    cellar = Cellar(**payload.model_dump())
    session.add(cellar)
    commit_or_400(session)
    session.refresh(cellar)
    return cellar


@router.get("/{cellar_id}", response_model=CellarRead)
def get_cellar(cellar_id: str, session: Session = Depends(get_session)) -> Cellar:
    return get_or_404(session, Cellar, cellar_id, "Cellar")


@router.patch("/{cellar_id}", response_model=CellarRead)
def update_cellar(cellar_id: str, payload: CellarUpdate, session: Session = Depends(get_session)) -> Cellar:
    cellar = get_or_404(session, Cellar, cellar_id, "Cellar")
    apply_update(cellar, payload.model_dump(exclude_unset=True))
    commit_or_400(session)
    session.refresh(cellar)
    return cellar


@router.get("/{cellar_id}/locations", response_model=list[LocationRead])
def list_cellar_locations(cellar_id: str, session: Session = Depends(get_session)) -> list[dict]:
    get_or_404(session, Cellar, cellar_id, "Cellar")
    locations = session.scalars(
        select(Location)
        .options(joinedload(Location.cellar))
        .where(Location.cellar_id == cellar_id)
        .order_by(Location.row_index, Location.column_index, Location.code)
    ).all()
    return [location_to_read(location) for location in locations]


@router.post("/{cellar_id}/locations", response_model=LocationRead, status_code=201)
def create_cellar_location(
    cellar_id: str,
    payload: LocationCreate,
    session: Session = Depends(get_session),
) -> dict:
    get_or_404(session, Cellar, cellar_id, "Cellar")
    values = payload.model_dump()
    values["cellar_id"] = cellar_id
    location = Location(**values)
    session.add(location)
    commit_or_400(session)
    location = session.scalars(select(Location).options(joinedload(Location.cellar)).where(Location.id == location.id)).one()
    return location_to_read(location)


@router.post("/{cellar_id}/locations/batch", response_model=list[LocationRead], status_code=201)
def batch_create_cellar_locations(
    cellar_id: str,
    payload: CellarLocationBatchCreate,
    session: Session = Depends(get_session),
) -> list[dict]:
    cellar = get_or_404(session, Cellar, cellar_id, "Cellar")
    existing_codes = set(
        session.scalars(select(Location.code).where(Location.cellar_id == cellar_id)).all()
    )
    for row in range(1, payload.rows + 1):
        for column in range(1, payload.columns + 1):
            code = f"{payload.code_prefix}-{row:02d}-{column:02d}"
            if code in existing_codes:
                continue
            session.add(
                Location(
                    cellar_id=cellar_id,
                    code=code,
                    row_index=row,
                    column_index=column,
                    capacity=payload.capacity,
                    location_type=payload.location_type,
                )
            )
            existing_codes.add(code)
    cellar.rows = max(cellar.rows or 0, payload.rows)
    cellar.columns = max(cellar.columns or 0, payload.columns)
    commit_or_400(session)
    locations = session.scalars(
        select(Location)
        .options(joinedload(Location.cellar))
        .where(Location.cellar_id == cellar_id)
        .order_by(Location.row_index, Location.column_index, Location.code)
    ).all()
    return [location_to_read(location) for location in locations]


@router.get("/{cellar_id}/grid", response_model=list[LocationRead])
def get_cellar_grid(cellar_id: str, session: Session = Depends(get_session)) -> list[dict]:
    return list_cellar_locations(cellar_id, session)
