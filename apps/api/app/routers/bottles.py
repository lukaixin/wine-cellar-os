from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Bottle, InventoryTransaction, Location, Vintage, Wine
from app.routers.helpers import apply_update, bottle_to_read, commit_or_400, get_or_404, transaction_to_read
from app.schemas.common import BottleCreate, BottleRead, BottleUpdate, InventoryTransactionRead
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/bottles", tags=["bottles"])


def _bottle_query():
    return select(Bottle).options(
        joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer),
        joinedload(Bottle.current_location).joinedload(Location.cellar),
    )


@router.get("", response_model=list[BottleRead])
def list_bottles(session: Session = Depends(get_session)) -> list[dict]:
    bottles = session.scalars(_bottle_query().order_by(Bottle.created_at.desc())).all()
    return [bottle_to_read(bottle) for bottle in bottles]


@router.post("", response_model=BottleRead, status_code=201)
def create_bottle(payload: BottleCreate, session: Session = Depends(get_session)) -> dict:
    bottle = InventoryService(session).create_bottle_with_in_transaction(payload)
    bottle = session.scalars(_bottle_query().where(Bottle.id == bottle.id)).one()
    return bottle_to_read(bottle)


@router.get("/{bottle_id}", response_model=BottleRead)
def get_bottle(bottle_id: str, session: Session = Depends(get_session)) -> dict:
    bottle = session.scalars(_bottle_query().where(Bottle.id == bottle_id)).first()
    if bottle is None:
        get_or_404(session, Bottle, bottle_id, "Bottle")
    return bottle_to_read(bottle)


@router.patch("/{bottle_id}", response_model=BottleRead)
def update_bottle(bottle_id: str, payload: BottleUpdate, session: Session = Depends(get_session)) -> dict:
    bottle = get_or_404(session, Bottle, bottle_id, "Bottle")
    apply_update(bottle, payload.model_dump(exclude_unset=True))
    commit_or_400(session)
    bottle = session.scalars(_bottle_query().where(Bottle.id == bottle.id)).one()
    return bottle_to_read(bottle)


@router.get("/{bottle_id}/transactions", response_model=list[InventoryTransactionRead])
def list_bottle_transactions(bottle_id: str, session: Session = Depends(get_session)) -> list[dict]:
    get_or_404(session, Bottle, bottle_id, "Bottle")
    transactions = session.scalars(
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.bottle).joinedload(Bottle.vintage).joinedload(Vintage.wine),
            joinedload(InventoryTransaction.from_location),
            joinedload(InventoryTransaction.to_location),
        )
        .where(InventoryTransaction.bottle_id == bottle_id)
        .order_by(InventoryTransaction.occurred_at.asc(), InventoryTransaction.created_at.asc())
    ).all()
    return [transaction_to_read(transaction) for transaction in transactions]
