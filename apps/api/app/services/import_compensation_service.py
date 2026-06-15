from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Bottle, ImportBatch, ImportBatchRow, InventoryTransaction
from app.models.base import utcnow
from app.schemas.common import ImportBatchCompensationRequest, InventoryTransactionCreate
from app.services.inventory_service import InventoryService


def row_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


@dataclass(frozen=True)
class CompensationPlan:
    bottle_ids: list[str]
    import_transaction_ids: list[str]
    blockers: list[str]

    @property
    def can_compensate(self) -> bool:
        return not self.blockers and bool(self.bottle_ids)


class ImportCompensationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def plan(self, batch: ImportBatch, rows: list[ImportBatchRow] | None = None) -> CompensationPlan:
        if rows is None:
            rows = list(
                self.session.scalars(
                    select(ImportBatchRow)
                    .where(ImportBatchRow.batch_id == batch.id)
                    .order_by(ImportBatchRow.source_row_number)
                ).all()
            )

        bottle_ids: list[str] = []
        import_transaction_ids: list[str] = []
        blockers: list[str] = []

        if batch.status != "confirmed":
            blockers.append(f"Batch status is {batch.status}; only confirmed batches can be compensated.")
        if batch.compensated_at is not None or row_list(batch.compensation_transaction_ids):
            blockers.append("Batch has already been compensated.")

        for row in rows:
            bottle_ids.extend(str(item) for item in row_list(row.created_bottle_ids))
            import_transaction_ids.extend(str(item) for item in row_list(row.created_transaction_ids))

        if not bottle_ids:
            blockers.append("Batch has no created bottle IDs.")
        if len(bottle_ids) != len(import_transaction_ids):
            blockers.append("Created bottle count does not match import ledger transaction count.")

        seen_bottles: set[str] = set()
        seen_transactions: set[str] = set()
        for index, bottle_id in enumerate(bottle_ids):
            if bottle_id in seen_bottles:
                blockers.append(f"Duplicate created bottle id in batch rows: {bottle_id}.")
            seen_bottles.add(bottle_id)

            import_transaction_id = import_transaction_ids[index] if index < len(import_transaction_ids) else None
            if import_transaction_id is None:
                continue
            if import_transaction_id in seen_transactions:
                blockers.append(f"Duplicate import transaction id in batch rows: {import_transaction_id}.")
            seen_transactions.add(import_transaction_id)

            bottle = self.session.get(Bottle, bottle_id)
            if bottle is None:
                blockers.append(f"Created bottle is missing: {bottle_id}.")
                continue
            if bottle.current_status != "in_stock":
                blockers.append(f"Bottle {bottle_id} is {bottle.current_status}; only untouched in-stock bottles can be compensated.")
            if bottle.current_location_id is None:
                blockers.append(f"Bottle {bottle_id} has no current location.")

            import_transaction = self.session.get(InventoryTransaction, import_transaction_id)
            if import_transaction is None:
                blockers.append(f"Import transaction is missing: {import_transaction_id}.")
                continue
            if import_transaction.bottle_id != bottle_id or import_transaction.transaction_type != "IN":
                blockers.append(f"Import transaction {import_transaction_id} does not match bottle {bottle_id}.")
                continue

            transaction_count = self.session.scalar(
                select(InventoryTransaction.id).where(
                    InventoryTransaction.bottle_id == bottle_id,
                    InventoryTransaction.id != import_transaction_id,
                ).limit(1)
            )
            if transaction_count is not None:
                blockers.append(f"Bottle {bottle_id} already has post-import ledger activity.")

        return CompensationPlan(
            bottle_ids=bottle_ids,
            import_transaction_ids=import_transaction_ids,
            blockers=sorted(set(blockers)),
        )

    def compensate(self, batch: ImportBatch, request: ImportBatchCompensationRequest) -> dict[str, Any]:
        rows = list(
            self.session.scalars(
                select(ImportBatchRow)
                .where(ImportBatchRow.batch_id == batch.id)
                .order_by(ImportBatchRow.source_row_number)
            ).all()
        )
        plan = self.plan(batch, rows)
        if plan.blockers:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=plan.blockers)
        if request.confirm_bottle_count != len(plan.bottle_ids):
            raise HTTPException(
                status_code=422,
                detail=f"confirm_bottle_count must equal impacted bottle count {len(plan.bottle_ids)}",
            )

        service = InventoryService(self.session)
        compensation_transaction_ids: list[str] = []
        try:
            for bottle_id in plan.bottle_ids:
                bottle = self.session.get(Bottle, bottle_id)
                assert bottle is not None
                transaction = service.apply_transaction(
                    InventoryTransactionCreate(
                        bottle_id=bottle.id,
                        transaction_type="ADJUST",
                        from_location_id=bottle.current_location_id,
                        to_location_id=None,
                        actor="import_compensation",
                        reason=f"Import batch compensation: {batch.id}",
                        note=f"Compensated import batch {batch.id}: {request.reason}",
                    ),
                    commit=False,
                )
                compensation_transaction_ids.append(transaction.id)

            compensated_at = utcnow()
            batch.compensated_at = compensated_at
            batch.compensation_reason = request.reason
            batch.compensation_transaction_ids = compensation_transaction_ids
            self.session.add(batch)
            self.session.commit()
            return {
                "batch_id": batch.id,
                "compensated_bottles": len(plan.bottle_ids),
                "compensation_transaction_ids": compensation_transaction_ids,
                "compensated_at": compensated_at,
                "transaction_type": "ADJUST",
                "status": "compensated",
            }
        except Exception:
            self.session.rollback()
            raise
