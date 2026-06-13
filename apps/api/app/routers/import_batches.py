from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.models import ImportBatch, ImportBatchRow
from app.routers.helpers import get_or_404
from app.schemas.common import ImportBatchDetailResponse, ImportBatchListResponse

router = APIRouter(prefix="/imports", tags=["import_batches"])
api_router = APIRouter(prefix="/api/imports", tags=["import_batches"])


@dataclass(frozen=True)
class BatchStats:
    success_rows: int
    warning_rows: int
    error_rows: int
    created_bottle_count: int


def _row_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _batch_stats(rows: list[ImportBatchRow]) -> BatchStats:
    success_rows = sum(1 for row in rows if row.status == "imported")
    if success_rows == 0:
        success_rows = sum(1 for row in rows if row.status == "valid")
    return BatchStats(
        success_rows=success_rows,
        warning_rows=sum(1 for row in rows if _row_list(row.warnings)),
        error_rows=sum(1 for row in rows if row.status == "invalid" or _row_list(row.errors)),
        created_bottle_count=sum(len(_row_list(row.created_bottle_ids)) for row in rows),
    )


def _batch_to_list_item(batch: ImportBatch, rows: list[ImportBatchRow]) -> dict[str, Any]:
    stats = _batch_stats(rows)
    return {
        "id": batch.id,
        "filename": batch.source_filename,
        "status": batch.status,
        "created_at": batch.created_at,
        "confirmed_at": batch.confirmed_at,
        "total_rows": batch.row_count,
        "success_rows": stats.success_rows,
        "warning_rows": stats.warning_rows,
        "error_rows": stats.error_rows,
        "created_bottle_count": stats.created_bottle_count,
    }


def _row_to_detail(row: ImportBatchRow) -> dict[str, Any]:
    normalized = row.normalized_row if isinstance(row.normalized_row, dict) else {}
    return {
        "row_number": row.source_row_number,
        "raw_values": row.raw_row,
        "parsed_producer": normalized.get("producer_name"),
        "parsed_wine": normalized.get("wine_name"),
        "parsed_vintage": normalized.get("vintage_year"),
        "quantity": normalized.get("quantity"),
        "warnings": _row_list(row.warnings),
        "errors": _row_list(row.errors),
        "created_bottle_ids": _row_list(row.created_bottle_ids),
        "ledger_transaction_ids": _row_list(row.created_transaction_ids),
    }


def _list_import_batches(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    total = session.scalar(select(func.count(ImportBatch.id))) or 0
    batches = session.scalars(
        select(ImportBatch)
        .order_by(ImportBatch.created_at.desc(), ImportBatch.id.desc())
        .offset(offset)
        .limit(limit)
    ).all()
    batch_ids = [batch.id for batch in batches]
    rows_by_batch: dict[str, list[ImportBatchRow]] = {batch_id: [] for batch_id in batch_ids}
    if batch_ids:
        rows = session.scalars(
            select(ImportBatchRow)
            .where(ImportBatchRow.batch_id.in_(batch_ids))
            .order_by(ImportBatchRow.source_row_number.asc())
        ).all()
        for row in rows:
            rows_by_batch.setdefault(row.batch_id, []).append(row)
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [_batch_to_list_item(batch, rows_by_batch.get(batch.id, [])) for batch in batches],
    }


def _get_import_batch_detail(batch_id: str, session: Session = Depends(get_session)) -> dict[str, Any]:
    batch = get_or_404(session, ImportBatch, batch_id, "Import batch")
    rows = session.scalars(
        select(ImportBatchRow)
        .where(ImportBatchRow.batch_id == batch.id)
        .order_by(ImportBatchRow.source_row_number.asc())
    ).all()
    stats = _batch_stats(rows)
    return {
        "id": batch.id,
        "filename": batch.source_filename,
        "sheet_name": batch.sheet_name,
        "file_sha256": batch.file_sha256,
        "status": batch.status,
        "created_at": batch.created_at,
        "confirmed_at": batch.confirmed_at,
        "total_rows": batch.row_count,
        "success_rows": stats.success_rows,
        "warning_rows": stats.warning_rows,
        "error_rows": stats.error_rows,
        "created_bottle_count": stats.created_bottle_count,
        "warnings": _row_list(batch.warnings),
        "rows": [_row_to_detail(row) for row in rows],
    }


router.get("/batches", response_model=ImportBatchListResponse)(_list_import_batches)
router.get("/batches/{batch_id}", response_model=ImportBatchDetailResponse)(_get_import_batch_detail)
api_router.get("/batches", response_model=ImportBatchListResponse)(_list_import_batches)
api_router.get("/batches/{batch_id}", response_model=ImportBatchDetailResponse)(_get_import_batch_detail)
