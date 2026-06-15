from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.schemas.common import BackupCreateResponse, BackupListResponse, RestoreRequest, RestoreResponse
from app.services.safety_service import SafetyService

router = APIRouter(prefix="/admin", tags=["safety"])
api_router = APIRouter(prefix="/api/admin", tags=["safety"])


def _list_backups() -> dict[str, Any]:
    return SafetyService().list_backups()


def _create_backup() -> dict[str, Any]:
    return SafetyService().create_backup()


def _restore_backup(payload: RestoreRequest) -> dict[str, Any]:
    return SafetyService().restore_backup(
        filename=payload.filename,
        confirmation_text=payload.confirmation_text,
        reason=payload.reason,
    )


router.get("/backups", response_model=BackupListResponse)(_list_backups)
router.post("/backups", response_model=BackupCreateResponse, status_code=201)(_create_backup)
router.post("/backups/restore", response_model=RestoreResponse)(_restore_backup)
api_router.get("/backups", response_model=BackupListResponse)(_list_backups)
api_router.post("/backups", response_model=BackupCreateResponse, status_code=201)(_create_backup)
api_router.post("/backups/restore", response_model=RestoreResponse)(_restore_backup)
