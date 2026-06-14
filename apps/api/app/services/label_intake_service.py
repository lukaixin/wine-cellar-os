from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Bottle, Cellar, LabelImageUpload, Location, Producer, Vintage, Wine
from app.schemas.common import (
    BottleCreate,
    LabelDraftConfirmRequest,
    LabelDraftConfirmResponse,
    LabelDraftCandidateFields,
    LabelDraftRequest,
    LabelDraftResponse,
    LabelImageUploadRead,
)
from app.services.inventory_service import InventoryService
from app.services.label_recognizer import LabelRecognizer, MockLabelRecognizer
from app.services.registry_service import RegistryService

ALLOWED_LABEL_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class LabelIntakeService:
    session: Session
    recognizer: LabelRecognizer = MockLabelRecognizer()

    async def save_upload(self, file: UploadFile, bottle_id: str | None = None) -> LabelImageUpload:
        settings = get_settings()
        if file.content_type not in ALLOWED_LABEL_CONTENT_TYPES:
            raise HTTPException(status_code=415, detail="Only jpg, jpeg, png, and webp label images are allowed")
        if bottle_id is not None and self.session.get(Bottle, bottle_id) is None:
            raise HTTPException(status_code=404, detail="Bottle not found")

        data_dir = self._resolved_data_dir(settings.data_dir)
        upload_dir = self._resolved_upload_dir(settings.label_upload_dir, data_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        chunks: list[bytes] = []
        size = 0
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.label_max_upload_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"Label image exceeds {settings.label_max_upload_bytes} bytes",
                )
            digest.update(chunk)
            chunks.append(chunk)
        if size == 0:
            raise HTTPException(status_code=422, detail="Label image file is empty")

        sha256 = digest.hexdigest()
        extension = self._extension_for(file.filename or "", file.content_type or "")
        stored_filename = f"{uuid4()}-{sha256[:12]}{extension}"
        target = (upload_dir / stored_filename).resolve()
        if not self._is_relative_to(target, data_dir):
            raise HTTPException(status_code=500, detail="Resolved upload path is outside data directory")
        target.write_bytes(b"".join(chunks))

        upload = LabelImageUpload(
            original_filename=self._safe_original_filename(file.filename),
            stored_filename=stored_filename,
            content_type=file.content_type or "application/octet-stream",
            size_bytes=size,
            sha256=sha256,
            file_path=target.relative_to(data_dir).as_posix(),
            bottle_id=bottle_id,
        )
        self.session.add(upload)
        self.session.commit()
        self.session.refresh(upload)
        return upload

    def create_draft(self, payload: LabelDraftRequest) -> LabelDraftResponse:
        upload = self._get_upload(payload.upload_id)
        result = self.recognizer.recognize(upload)
        return LabelDraftResponse(
            upload=LabelImageUploadRead.model_validate(upload),
            recognizer=result.recognizer,
            confidence=result.confidence,
            candidate_fields=LabelDraftCandidateFields(**result.fields.__dict__),
            warnings=result.warnings,
        )

    def confirm(self, payload: LabelDraftConfirmRequest) -> LabelDraftConfirmResponse:
        upload = self._get_upload(payload.upload_id)
        location = self._get_location(payload.location_id)
        producer = self._get_or_create_producer(payload)
        wine = self._get_or_create_wine(payload, producer)
        vintage = self._get_or_create_vintage(payload, wine)
        self.session.flush()
        bottle = InventoryService(self.session).create_bottle_with_in_transaction(
            BottleCreate(
                vintage_id=vintage.id,
                current_location_id=location.id,
                bottle_size_ml=payload.bottle_size_ml,
                purchase_currency="CNY",
                personal_notes=payload.notes,
                actor="label_intake",
                note=f"Label intake confirmed from upload {upload.id}",
            )
        )
        upload.bottle_id = bottle.id
        self.session.add(upload)
        self.session.commit()
        return LabelDraftConfirmResponse(
            bottle_id=bottle.id,
            upload_id=upload.id,
            transaction_type="IN",
        )

    def _get_upload(self, upload_id: str) -> LabelImageUpload:
        upload = self.session.get(LabelImageUpload, upload_id)
        if upload is None:
            raise HTTPException(status_code=404, detail="Label image upload not found")
        return upload

    def _get_location(self, location_id: str) -> Location:
        location = self.session.get(Location, location_id)
        if location is None:
            raise HTTPException(status_code=404, detail="Location not found")
        return location

    def _get_or_create_producer(self, payload: LabelDraftConfirmRequest) -> Producer:
        registry = RegistryService(self.session)
        producer = self.session.scalar(
            select(Producer).where(func.lower(Producer.name_original) == payload.producer_name.lower())
        )
        if producer is not None:
            registry.apply_producer_fields(producer)
            return producer
        producer = Producer(
            name_original=payload.producer_name,
            country=payload.country,
            region=payload.region,
        )
        registry.apply_producer_fields(producer)
        self.session.add(producer)
        self.session.flush()
        return producer

    def _get_or_create_wine(self, payload: LabelDraftConfirmRequest, producer: Producer) -> Wine:
        registry = RegistryService(self.session)
        wine = self.session.scalar(
            select(Wine).where(
                Wine.producer_id == producer.id,
                func.lower(Wine.name_original) == payload.wine_name.lower(),
            )
        )
        if wine is not None:
            registry.apply_wine_fields(wine, producer)
            return wine
        wine = Wine(
            producer_id=producer.id,
            name_original=payload.wine_name,
            type=payload.type,
            country=payload.country,
            region=payload.region,
        )
        registry.apply_wine_fields(wine, producer)
        self.session.add(wine)
        self.session.flush()
        return wine

    def _get_or_create_vintage(self, payload: LabelDraftConfirmRequest, wine: Wine) -> Vintage:
        registry = RegistryService(self.session)
        vintage = self.session.scalar(
            select(Vintage).where(
                Vintage.wine_id == wine.id,
                Vintage.vintage_year == payload.vintage_year,
                Vintage.is_non_vintage.is_(False),
            )
        )
        if vintage is not None:
            registry.apply_vintage_fields(vintage)
            return vintage
        vintage = Vintage(
            wine_id=wine.id,
            vintage_year=payload.vintage_year,
            is_non_vintage=False,
        )
        registry.apply_vintage_fields(vintage)
        self.session.add(vintage)
        self.session.flush()
        return vintage

    def _resolved_data_dir(self, raw_path: str) -> Path:
        return Path(raw_path).resolve()

    def _resolved_upload_dir(self, raw_path: str, data_dir: Path) -> Path:
        path = Path(raw_path)
        if not path.is_absolute():
            path = data_dir / path
        resolved = path.resolve()
        if not self._is_relative_to(resolved, data_dir):
            raise HTTPException(status_code=500, detail="Label upload directory must be inside project data directory")
        return resolved

    def _extension_for(self, filename: str, content_type: str) -> str:
        by_type = ALLOWED_LABEL_CONTENT_TYPES.get(content_type)
        suffix = Path(filename).suffix.lower()
        if content_type == "image/jpeg" and suffix in {".jpg", ".jpeg"}:
            return suffix
        if by_type and (not suffix or suffix == by_type):
            return by_type
        if by_type and suffix in {".jpg", ".jpeg", ".png", ".webp"}:
            return by_type
        return by_type or ".bin"

    def _safe_original_filename(self, filename: str | None) -> str:
        value = Path(filename or "label-image").name
        return re.sub(r"[\r\n\t]", "_", value)[:240] or "label-image"

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False
