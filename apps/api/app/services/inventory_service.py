from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bottle, InventoryTransaction, Location, Vintage
from app.models.base import utcnow
from app.schemas.common import BottleCreate, InventoryTransactionCreate

SUPPORTED_TRANSACTION_TYPES = {"IN", "MOVE", "CONSUME", "GIFT", "DAMAGE", "ADJUST"}
OUTBOUND_TRANSACTION_TYPES = {"CONSUME", "GIFT", "DAMAGE"}


@dataclass(frozen=True)
class BottleCreationResult:
    bottle: Bottle
    transaction: InventoryTransaction


@dataclass(frozen=True)
class InventoryService:
    session: Session

    def create_bottle_with_in_transaction(self, payload: BottleCreate, commit: bool = True) -> Bottle:
        return self.create_bottle_with_in_transaction_result(payload, commit=commit).bottle

    def create_bottle_with_in_transaction_result(
        self,
        payload: BottleCreate,
        commit: bool = True,
    ) -> BottleCreationResult:
        self._get_vintage(payload.vintage_id)
        to_location = self._get_location(payload.current_location_id)
        self._validate_location_has_capacity(to_location)

        bottle = Bottle(
            vintage_id=payload.vintage_id,
            bottle_size_ml=payload.bottle_size_ml,
            lwin16=payload.lwin16,
            acquisition_date=payload.acquisition_date,
            purchase_price=payload.purchase_price,
            purchase_currency=payload.purchase_currency,
            purchase_source=payload.purchase_source,
            purchase_channel=payload.purchase_channel,
            ws_price=payload.ws_price,
            condition=payload.condition,
            current_status="in_stock",
            current_location_id=to_location.id,
            personal_rating=payload.personal_rating,
            personal_notes=payload.personal_notes,
        )
        self.session.add(bottle)
        self.session.flush()
        transaction = self._add_transaction(
            bottle=bottle,
            transaction_type="IN",
            to_location_id=to_location.id,
            actor=payload.actor,
            note=payload.note,
        )
        if commit:
            self.session.commit()
            self.session.refresh(bottle)
            self.session.refresh(transaction)
        return BottleCreationResult(bottle=bottle, transaction=transaction)

    def apply_transaction(self, payload: InventoryTransactionCreate) -> InventoryTransaction:
        transaction_type = payload.transaction_type.upper()
        if transaction_type not in SUPPORTED_TRANSACTION_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"transaction_type must be one of {sorted(SUPPORTED_TRANSACTION_TYPES)}",
            )

        bottle = self._get_bottle(payload.bottle_id)
        if transaction_type == "MOVE" and bottle.current_status != "in_stock":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only in-stock bottles can move")

        from_location_id = payload.from_location_id
        to_location_id = payload.to_location_id

        if transaction_type in {"MOVE", *OUTBOUND_TRANSACTION_TYPES} and from_location_id is None:
            from_location_id = bottle.current_location_id
        if from_location_id is not None:
            self._get_location(from_location_id)
        if to_location_id is not None:
            to_location = self._get_location(to_location_id)
            self._validate_location_has_capacity(to_location, bottle.id)

        self._validate_transaction(bottle, transaction_type, from_location_id, to_location_id, payload.note)
        self._apply_bottle_snapshot(bottle, transaction_type, to_location_id)
        transaction = self._add_transaction(
            bottle=bottle,
            transaction_type=transaction_type,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            actor=payload.actor,
            reason=payload.reason,
            note=payload.note,
            occurred_at=payload.occurred_at,
        )
        self.session.commit()
        self.session.refresh(transaction)
        return transaction

    def _validate_transaction(
        self,
        bottle: Bottle,
        transaction_type: str,
        from_location_id: str | None,
        to_location_id: str | None,
        note: str | None,
    ) -> None:
        if transaction_type == "IN" and to_location_id is None:
            raise HTTPException(status_code=422, detail="IN requires to_location_id")
        if transaction_type == "MOVE":
            if from_location_id is None or to_location_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="MOVE requires from_location_id and to_location_id",
                )
            if bottle.current_status != "in_stock":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only in-stock bottles can move")
            self._validate_from_location_matches_current(bottle, from_location_id)
            if from_location_id == to_location_id:
                raise HTTPException(
                    status_code=422,
                    detail="MOVE requires a different to_location_id",
                )
        if transaction_type in OUTBOUND_TRANSACTION_TYPES:
            if bottle.current_status != "in_stock":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Cannot create {transaction_type}: bottle is already unavailable "
                        f"with status {bottle.current_status}"
                    ),
                )
            if from_location_id is None:
                raise HTTPException(
                    status_code=422,
                    detail=f"{transaction_type} requires from_location_id or a current bottle location",
                )
            self._validate_from_location_matches_current(bottle, from_location_id)
        if transaction_type == "ADJUST":
            if from_location_id is None and to_location_id is None:
                raise HTTPException(
                    status_code=422,
                    detail="ADJUST requires from_location_id or to_location_id",
                )
            if not note:
                raise HTTPException(
                    status_code=422,
                    detail="ADJUST requires note for audit context",
                )
            if from_location_id is not None and bottle.current_location_id is not None:
                self._validate_from_location_matches_current(bottle, from_location_id)

    def _apply_bottle_snapshot(self, bottle: Bottle, transaction_type: str, to_location_id: str | None) -> None:
        if transaction_type == "IN":
            bottle.current_status = "in_stock"
            bottle.current_location_id = to_location_id
        elif transaction_type == "MOVE":
            bottle.current_location_id = to_location_id
        elif transaction_type == "CONSUME":
            bottle.current_status = "drunk"
            bottle.current_location_id = None
        elif transaction_type == "GIFT":
            bottle.current_status = "gifted"
            bottle.current_location_id = None
        elif transaction_type == "DAMAGE":
            bottle.current_status = "damaged"
            bottle.current_location_id = None
        elif transaction_type == "ADJUST" and to_location_id is not None:
            bottle.current_status = "in_stock"
            bottle.current_location_id = to_location_id
        elif transaction_type == "ADJUST":
            bottle.current_status = "lost"
            bottle.current_location_id = None
        self.session.add(bottle)

    def _validate_from_location_matches_current(self, bottle: Bottle, from_location_id: str) -> None:
        if bottle.current_location_id != from_location_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="from_location_id must match bottle current_location_id",
            )

    def _validate_location_has_capacity(self, location: Location, moving_bottle_id: str | None = None) -> None:
        query = select(func.count(Bottle.id)).where(
            Bottle.current_location_id == location.id,
            Bottle.current_status == "in_stock",
        )
        if moving_bottle_id is not None:
            query = query.where(Bottle.id != moving_bottle_id)
        occupied = self.session.scalar(query) or 0
        if occupied >= location.capacity:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location {location.code} is full ({occupied}/{location.capacity})",
            )

    def _add_transaction(
        self,
        bottle: Bottle,
        transaction_type: str,
        from_location_id: str | None = None,
        to_location_id: str | None = None,
        actor: str | None = None,
        reason: str | None = None,
        note: str | None = None,
        occurred_at: datetime | None = None,
    ) -> InventoryTransaction:
        transaction = InventoryTransaction(
            bottle_id=bottle.id,
            transaction_type=transaction_type,
            from_location_id=from_location_id,
            to_location_id=to_location_id,
            actor=actor,
            reason=reason,
            note=note,
            occurred_at=occurred_at or utcnow(),
        )
        self.session.add(transaction)
        self.session.flush()
        return transaction

    def _get_bottle(self, bottle_id: str) -> Bottle:
        bottle = self.session.get(Bottle, bottle_id)
        if bottle is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bottle not found")
        return bottle

    def _get_location(self, location_id: str) -> Location:
        location = self.session.get(Location, location_id)
        if location is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location not found")
        return location

    def _get_vintage(self, vintage_id: str) -> Vintage:
        vintage = self.session.get(Vintage, vintage_id)
        if vintage is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vintage not found")
        return vintage
