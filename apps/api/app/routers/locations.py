from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Cellar, Location
from app.routers.helpers import apply_update, commit_or_400, get_or_404, location_to_read
from app.schemas.common import LocationCreate, LocationRead, LocationUpdate

router = APIRouter(prefix="/api/locations", tags=["locations"])


@router.get("", response_model=list[LocationRead])
def list_locations(session: Session = Depends(get_session)) -> list[dict]:
    locations = session.scalars(
        select(Location).options(joinedload(Location.cellar)).order_by(Location.code)
    ).all()
    return [location_to_read(location) for location in locations]


@router.post("", response_model=LocationRead, status_code=201)
def create_location(payload: LocationCreate, session: Session = Depends(get_session)) -> dict:
    get_or_404(session, Cellar, payload.cellar_id, "Cellar")
    location = Location(**payload.model_dump())
    session.add(location)
    commit_or_400(session)
    location = session.scalars(select(Location).options(joinedload(Location.cellar)).where(Location.id == location.id)).one()
    return location_to_read(location)


@router.get("/{location_id}", response_model=LocationRead)
def get_location(location_id: str, session: Session = Depends(get_session)) -> dict:
    location = session.scalars(select(Location).options(joinedload(Location.cellar)).where(Location.id == location_id)).first()
    if location is None:
        get_or_404(session, Location, location_id, "Location")
    return location_to_read(location)


@router.patch("/{location_id}", response_model=LocationRead)
def update_location(location_id: str, payload: LocationUpdate, session: Session = Depends(get_session)) -> dict:
    location = get_or_404(session, Location, location_id, "Location")
    values = payload.model_dump(exclude_unset=True)
    if "cellar_id" in values:
        get_or_404(session, Cellar, values["cellar_id"], "Cellar")
    apply_update(location, values)
    commit_or_400(session)
    location = session.scalars(select(Location).options(joinedload(Location.cellar)).where(Location.id == location.id)).one()
    return location_to_read(location)
