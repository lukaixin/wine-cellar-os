from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.common import (
    CsvImportConfirmRequest,
    CsvImportConfirmResponse,
    CsvImportDraftRequest,
    CsvImportDraftResponse,
)
from app.services.csv_import_service import CsvImportService

router = APIRouter(prefix="/api/import/csv", tags=["csv_import"])


@router.post("/draft", response_model=CsvImportDraftResponse)
def create_csv_import_draft(
    payload: CsvImportDraftRequest,
    session: Session = Depends(get_session),
) -> CsvImportDraftResponse:
    return CsvImportService(session).parse_draft(payload)


@router.post("/confirm", response_model=CsvImportConfirmResponse, status_code=201)
def confirm_csv_import(
    payload: CsvImportConfirmRequest,
    session: Session = Depends(get_session),
) -> CsvImportConfirmResponse:
    return CsvImportService(session).confirm(payload)
