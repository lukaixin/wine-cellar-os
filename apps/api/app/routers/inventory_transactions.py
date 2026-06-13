from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Bottle, InventoryTransaction, Vintage
from app.routers.helpers import transaction_to_read
from app.schemas.common import InventoryTransactionCreate, InventoryTransactionRead
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/api/inventory-transactions", tags=["inventory_transactions"])


@router.get("", response_model=list[InventoryTransactionRead])
def list_inventory_transactions(session: Session = Depends(get_session)) -> list[dict]:
    transactions = session.scalars(
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.bottle).joinedload(Bottle.vintage).joinedload(Vintage.wine),
            joinedload(InventoryTransaction.from_location),
            joinedload(InventoryTransaction.to_location),
        )
        .order_by(InventoryTransaction.occurred_at.desc())
    ).all()
    return [transaction_to_read(transaction) for transaction in transactions]


@router.post("", response_model=InventoryTransactionRead, status_code=201)
def create_inventory_transaction(
    payload: InventoryTransactionCreate,
    session: Session = Depends(get_session),
) -> dict:
    transaction = InventoryService(session).apply_transaction(payload)
    transaction = session.scalars(
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.bottle).joinedload(Bottle.vintage).joinedload(Vintage.wine),
            joinedload(InventoryTransaction.from_location),
            joinedload(InventoryTransaction.to_location),
        )
        .where(InventoryTransaction.id == transaction.id)
    ).one()
    return transaction_to_read(transaction)
