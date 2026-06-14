from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Bottle, InventoryTransaction, Vintage
from app.routers.helpers import transaction_to_read
from app.schemas.common import (
    ConsumeBottleAction,
    DamageBottleAction,
    GiftBottleAction,
    InventoryTransactionCreate,
    InventoryTransactionRead,
    MoveBottleAction,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/inventory/actions", tags=["inventory_actions"])
api_router = APIRouter(prefix="/api/inventory/actions", tags=["inventory_actions"])


def _validate_single_bottle_quantity(quantity: int) -> None:
    if quantity != 1:
        raise HTTPException(
            status_code=422,
            detail="quantity must be 1 because each Bottle record represents one physical bottle",
        )


def _load_transaction(session: Session, transaction_id: str) -> InventoryTransaction:
    return session.scalars(
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.bottle).joinedload(Bottle.vintage).joinedload(Vintage.wine),
            joinedload(InventoryTransaction.from_location),
            joinedload(InventoryTransaction.to_location),
        )
        .where(InventoryTransaction.id == transaction_id)
    ).one()


def _apply_action(session: Session, payload: InventoryTransactionCreate) -> dict:
    transaction = InventoryService(session).apply_transaction(payload)
    return transaction_to_read(_load_transaction(session, transaction.id))


def _consume(payload: ConsumeBottleAction, session: Session = Depends(get_session)) -> dict:
    _validate_single_bottle_quantity(payload.quantity)
    return _apply_action(
        session,
        InventoryTransactionCreate(
            bottle_id=payload.bottle_id,
            transaction_type="CONSUME",
            note=payload.notes,
        ),
    )


def _gift(payload: GiftBottleAction, session: Session = Depends(get_session)) -> dict:
    _validate_single_bottle_quantity(payload.quantity)
    return _apply_action(
        session,
        InventoryTransactionCreate(
            bottle_id=payload.bottle_id,
            transaction_type="GIFT",
            reason=f"Recipient: {payload.recipient}",
            note=payload.notes,
        ),
    )


def _damage(payload: DamageBottleAction, session: Session = Depends(get_session)) -> dict:
    _validate_single_bottle_quantity(payload.quantity)
    return _apply_action(
        session,
        InventoryTransactionCreate(
            bottle_id=payload.bottle_id,
            transaction_type="DAMAGE",
            reason=payload.reason,
            note=payload.notes,
        ),
    )


def _move(payload: MoveBottleAction, session: Session = Depends(get_session)) -> dict:
    return _apply_action(
        session,
        InventoryTransactionCreate(
            bottle_id=payload.bottle_id,
            transaction_type="MOVE",
            from_location_id=payload.from_location,
            to_location_id=payload.to_location,
            note=payload.notes,
        ),
    )


for target_router in (router, api_router):
    target_router.post("/consume", response_model=InventoryTransactionRead, status_code=201)(_consume)
    target_router.post("/gift", response_model=InventoryTransactionRead, status_code=201)(_gift)
    target_router.post("/damage", response_model=InventoryTransactionRead, status_code=201)(_damage)
    target_router.post("/move", response_model=InventoryTransactionRead, status_code=201)(_move)
