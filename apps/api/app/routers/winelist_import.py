from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.common import WineListImportConfirmResponse, WineListImportDraftResponse
from app.services.winelist_import_service import WineListImportService

router = APIRouter(prefix="/api/import/winelist", tags=["winelist_import"])


@router.post("/draft", response_model=WineListImportDraftResponse)
async def create_winelist_import_draft(
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
) -> WineListImportDraftResponse:
    content = await file.read()
    filename = file.filename or "WineList.xlsx"
    return WineListImportService(session).create_draft(filename, content)


@router.post("/{batch_id}/confirm", response_model=WineListImportConfirmResponse, status_code=201)
def confirm_winelist_import(
    batch_id: str,
    session: Session = Depends(get_session),
) -> WineListImportConfirmResponse:
    return WineListImportService(session).confirm(batch_id)
