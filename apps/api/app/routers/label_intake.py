from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.schemas.common import (
    LabelDraftConfirmRequest,
    LabelDraftConfirmResponse,
    LabelDraftRequest,
    LabelDraftResponse,
    LabelImageUploadRead,
)
from app.services.label_intake_service import LabelIntakeService

router = APIRouter(prefix="/api/intake", tags=["label_intake"])


@router.post("/label-images", response_model=LabelImageUploadRead, status_code=201)
async def upload_label_image(
    file: UploadFile = File(...),
    bottle_id: str | None = Form(default=None),
    session: Session = Depends(get_session),
) -> LabelImageUploadRead:
    upload = await LabelIntakeService(session).save_upload(file, bottle_id)
    return LabelImageUploadRead.model_validate(upload)


@router.post("/label-drafts", response_model=LabelDraftResponse)
def create_label_draft(
    payload: LabelDraftRequest,
    session: Session = Depends(get_session),
) -> LabelDraftResponse:
    return LabelIntakeService(session).create_draft(payload)


@router.post("/label-drafts/confirm", response_model=LabelDraftConfirmResponse, status_code=201)
def confirm_label_draft(
    payload: LabelDraftConfirmRequest,
    session: Session = Depends(get_session),
) -> LabelDraftConfirmResponse:
    return LabelIntakeService(session).confirm(payload)
