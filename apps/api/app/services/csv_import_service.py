from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Bottle, Cellar, Location, Producer, Vintage, Wine
from app.schemas.common import (
    BottleCreate,
    CsvImportConfirmRequest,
    CsvImportConfirmResponse,
    CsvImportDraftRequest,
    CsvImportDraftResponse,
    CsvImportDraftRow,
    CsvImportRow,
)
from app.services.inventory_service import BottleCreationResult, InventoryService

REQUIRED_FIELDS = [
    "producer_name",
    "wine_name",
    "vintage_year",
    "bottle_size_ml",
    "cellar_name",
    "location_code",
]

OPTIONAL_FIELDS = [
    "country",
    "region",
    "type",
    "purchase_price",
    "purchase_currency",
    "purchase_date",
    "purchase_source",
    "drink_from",
    "drink_to",
    "notes",
    "tags",
]


def _clean(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _header(value: object) -> str:
    return str(value or "").lstrip("\ufeff").strip().lower()


@dataclass(frozen=True)
class CsvImportService:
    session: Session

    def parse_draft(self, payload: CsvImportDraftRequest) -> CsvImportDraftResponse:
        text = payload.csv_text.lstrip("\ufeff")
        top_level_errors: list[str] = []
        rows: list[CsvImportDraftRow] = []

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            return CsvImportDraftResponse(
                filename=payload.filename,
                required_fields=REQUIRED_FIELDS,
                optional_fields=OPTIONAL_FIELDS,
                total_rows=0,
                valid_rows=0,
                invalid_rows=0,
                errors=["CSV header is required"],
                rows=[],
            )

        reader.fieldnames = [_header(field) for field in reader.fieldnames]
        missing_headers = [field for field in REQUIRED_FIELDS if field not in reader.fieldnames]
        if missing_headers:
            top_level_errors.append(f"Missing required CSV headers: {', '.join(missing_headers)}")

        for row_number, raw_row in enumerate(reader, start=2):
            if self._is_empty_row(raw_row):
                continue
            raw = {str(key): _clean(value) for key, value in raw_row.items() if key is not None}
            row_errors = [f"Missing required CSV header: {field}" for field in missing_headers]
            row_warnings: list[str] = []
            if None in raw_row:
                row_errors.append("Row has more values than headers")
            normalized = self._normalize_row(raw, row_errors, row_warnings)
            rows.append(
                CsvImportDraftRow(
                    row_number=row_number,
                    status="invalid" if row_errors else "valid",
                    raw=raw,
                    normalized=normalized,
                    errors=row_errors,
                    warnings=row_warnings,
                )
            )

        self._apply_batch_capacity_errors(rows)
        valid_rows = sum(1 for row in rows if row.status == "valid")
        invalid_rows = len(rows) - valid_rows
        return CsvImportDraftResponse(
            filename=payload.filename,
            required_fields=REQUIRED_FIELDS,
            optional_fields=OPTIONAL_FIELDS,
            total_rows=len(rows),
            valid_rows=valid_rows,
            invalid_rows=invalid_rows,
            errors=top_level_errors,
            rows=rows,
        )

    def confirm(self, payload: CsvImportConfirmRequest) -> CsvImportConfirmResponse:
        try:
            if not payload.rows:
                raise HTTPException(status_code=422, detail="No valid CSV import rows to confirm")

            resolved: list[tuple[CsvImportRow, Location]] = []
            errors: list[str] = []
            for index, row in enumerate(payload.rows, start=1):
                location, location_errors = self._resolve_location(row.cellar_name, row.location_code)
                if location_errors:
                    errors.extend(f"row {index}: {error}" for error in location_errors)
                elif location is not None:
                    resolved.append((row, location))

            errors.extend(self._capacity_errors_for_confirm(resolved))
            if errors:
                raise HTTPException(status_code=422, detail="; ".join(errors))

            created_ids: list[str] = []
            transaction_ids: list[str] = []
            warnings: list[str] = []
            for row, location in resolved:
                result = self._create_imported_bottle(row, location)
                created_ids.append(result.bottle.id)
                transaction_ids.append(result.transaction.id)
                if row.tags:
                    warnings.append(f"tags parsed but not persisted for bottle {result.bottle.id}")

            self.session.commit()
            return CsvImportConfirmResponse(
                created_bottles=len(created_ids),
                created_bottle_ids=created_ids,
                created_transaction_ids=transaction_ids,
                warnings=warnings,
            )
        except HTTPException:
            self.session.rollback()
            raise
        except Exception as exc:
            self.session.rollback()
            raise HTTPException(status_code=500, detail=f"CSV import confirm rolled back: {exc}") from exc

    def _normalize_row(
        self,
        raw: dict[str, str | None],
        errors: list[str],
        warnings: list[str],
    ) -> CsvImportRow | None:
        producer_name = self._required_text(raw, "producer_name", errors)
        wine_name = self._required_text(raw, "wine_name", errors)
        vintage_year = self._required_int(raw, "vintage_year", errors)
        bottle_size_ml = self._required_int(raw, "bottle_size_ml", errors)
        cellar_name = self._required_text(raw, "cellar_name", errors)
        location_code = self._required_text(raw, "location_code", errors)

        if bottle_size_ml is not None and bottle_size_ml <= 0:
            errors.append("bottle_size_ml must be greater than 0")
        if vintage_year is not None and vintage_year <= 0:
            errors.append("vintage_year must be greater than 0")

        purchase_price = self._optional_decimal(raw, "purchase_price", errors)
        purchase_date = self._optional_date(raw, "purchase_date", errors)
        drink_from = self._optional_int(raw, "drink_from", errors)
        drink_to = self._optional_int(raw, "drink_to", errors)
        if drink_from is not None and drink_to is not None and drink_from > drink_to:
            errors.append("drink_from must be less than or equal to drink_to")

        location: Location | None = None
        if cellar_name and location_code:
            location, location_errors = self._resolve_location(cellar_name, location_code)
            errors.extend(location_errors)

        tags = self._parse_tags(raw.get("tags"))
        if tags:
            warnings.append("tags are parsed in draft, but confirm does not persist tag relations yet")

        if errors:
            return None

        return CsvImportRow(
            producer_name=producer_name or "",
            wine_name=wine_name or "",
            vintage_year=vintage_year or 0,
            bottle_size_ml=bottle_size_ml or 750,
            cellar_name=cellar_name or "",
            location_code=location_code or "",
            country=raw.get("country"),
            region=raw.get("region"),
            type=raw.get("type"),
            purchase_price=purchase_price,
            purchase_currency=raw.get("purchase_currency") or "CNY",
            purchase_date=purchase_date,
            purchase_source=raw.get("purchase_source"),
            drink_from=drink_from,
            drink_to=drink_to,
            notes=raw.get("notes"),
            tags=tags,
            cellar_id=location.cellar_id if location else None,
            location_id=location.id if location else None,
        )

    def _apply_batch_capacity_errors(self, rows: list[CsvImportDraftRow]) -> None:
        valid_location_ids = [
            row.normalized.location_id
            for row in rows
            if row.status == "valid" and row.normalized is not None and row.normalized.location_id is not None
        ]
        pending_counts = Counter(valid_location_ids)
        for location_id, pending_count in pending_counts.items():
            location = self.session.get(Location, location_id)
            if location is None:
                continue
            occupied = self._occupied_count(location.id)
            if occupied + pending_count <= location.capacity:
                continue
            message = f"location capacity exceeded by import batch ({occupied}+{pending_count}/{location.capacity})"
            for row in rows:
                if row.normalized is not None and row.normalized.location_id == location_id:
                    row.errors.append(message)
                    row.status = "invalid"

    def _capacity_errors_for_confirm(self, resolved: list[tuple[CsvImportRow, Location]]) -> list[str]:
        pending_counts = Counter(location.id for _, location in resolved)
        errors: list[str] = []
        for location_id, pending_count in pending_counts.items():
            location = self.session.get(Location, location_id)
            if location is None:
                errors.append(f"location {location_id} not found")
                continue
            occupied = self._occupied_count(location.id)
            if occupied + pending_count > location.capacity:
                errors.append(
                    f"location {location.code} is full for import ({occupied}+{pending_count}/{location.capacity})"
                )
        return errors

    def _create_imported_bottle(self, row: CsvImportRow, location: Location) -> BottleCreationResult:
        producer = self._get_or_create_producer(row)
        wine = self._get_or_create_wine(row, producer)
        vintage = self._get_or_create_vintage(row, wine)
        self.session.flush()
        return InventoryService(self.session).create_bottle_with_in_transaction_result(
            BottleCreate(
                vintage_id=vintage.id,
                current_location_id=location.id,
                bottle_size_ml=row.bottle_size_ml,
                acquisition_date=row.purchase_date,
                purchase_price=row.purchase_price,
                purchase_currency=row.purchase_currency or "CNY",
                purchase_source=row.purchase_source,
                personal_notes=row.notes,
                actor="csv_import",
                note="CSV import confirmed",
            ),
            commit=False,
        )

    def _get_or_create_producer(self, row: CsvImportRow) -> Producer:
        producer = self.session.scalar(
            select(Producer).where(func.lower(Producer.name_original) == row.producer_name.lower())
        )
        if producer is not None:
            return producer
        producer = Producer(
            name_original=row.producer_name,
            country=row.country,
            region=row.region,
        )
        self.session.add(producer)
        self.session.flush()
        return producer

    def _get_or_create_wine(self, row: CsvImportRow, producer: Producer) -> Wine:
        wine = self.session.scalar(
            select(Wine).where(
                Wine.producer_id == producer.id,
                func.lower(Wine.name_original) == row.wine_name.lower(),
            )
        )
        if wine is not None:
            return wine
        wine = Wine(
            producer_id=producer.id,
            name_original=row.wine_name,
            type=row.type,
            country=row.country,
            region=row.region,
        )
        self.session.add(wine)
        self.session.flush()
        return wine

    def _get_or_create_vintage(self, row: CsvImportRow, wine: Wine) -> Vintage:
        vintage = self.session.scalar(
            select(Vintage).where(
                Vintage.wine_id == wine.id,
                Vintage.vintage_year == row.vintage_year,
                Vintage.is_non_vintage.is_(False),
            )
        )
        if vintage is not None:
            return vintage
        vintage = Vintage(
            wine_id=wine.id,
            vintage_year=row.vintage_year,
            is_non_vintage=False,
            default_drink_from=row.drink_from,
            default_drink_to=row.drink_to,
            drink_window_confidence="low" if row.drink_from or row.drink_to else None,
        )
        self.session.add(vintage)
        self.session.flush()
        return vintage

    def _resolve_location(self, cellar_name: str, location_code: str) -> tuple[Location | None, list[str]]:
        cellars = self.session.scalars(
            select(Cellar).where(func.lower(Cellar.name) == cellar_name.lower())
        ).all()
        if not cellars:
            return None, [f"cellar_name not found: {cellar_name}"]
        if len(cellars) > 1:
            return None, [f"cellar_name is ambiguous: {cellar_name}"]
        cellar = cellars[0]
        locations = self.session.scalars(
            select(Location).where(
                Location.cellar_id == cellar.id,
                func.lower(Location.code) == location_code.lower(),
            )
        ).all()
        if not locations:
            return None, [f"location_code not found in cellar {cellar_name}: {location_code}"]
        if len(locations) > 1:
            return None, [f"location_code is ambiguous in cellar {cellar_name}: {location_code}"]
        location = locations[0]
        if self._occupied_count(location.id) >= location.capacity:
            return None, [f"location_code is full: {cellar_name}/{location_code}"]
        return location, []

    def _occupied_count(self, location_id: str) -> int:
        return self.session.scalar(
            select(func.count(Bottle.id)).where(
                Bottle.current_location_id == location_id,
                Bottle.current_status == "in_stock",
            )
        ) or 0

    def _required_text(self, raw: dict[str, str | None], field: str, errors: list[str]) -> str | None:
        value = raw.get(field)
        if not value:
            errors.append(f"{field} is required")
            return None
        return value

    def _required_int(self, raw: dict[str, str | None], field: str, errors: list[str]) -> int | None:
        value = raw.get(field)
        if not value:
            errors.append(f"{field} is required")
            return None
        return self._parse_int(value, field, errors)

    def _optional_int(self, raw: dict[str, str | None], field: str, errors: list[str]) -> int | None:
        value = raw.get(field)
        if not value:
            return None
        return self._parse_int(value, field, errors)

    def _parse_int(self, value: str, field: str, errors: list[str]) -> int | None:
        try:
            return int(value)
        except ValueError:
            errors.append(f"{field} must be an integer")
            return None

    def _optional_decimal(self, raw: dict[str, str | None], field: str, errors: list[str]) -> Decimal | None:
        value = raw.get(field)
        if not value:
            return None
        try:
            parsed = Decimal(value)
        except InvalidOperation:
            errors.append(f"{field} must be a decimal")
            return None
        if parsed < 0:
            errors.append(f"{field} must be greater than or equal to 0")
            return None
        return parsed

    def _optional_date(self, raw: dict[str, str | None], field: str, errors: list[str]) -> date | None:
        value = raw.get(field)
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            errors.append(f"{field} must use YYYY-MM-DD")
            return None

    def _parse_tags(self, value: str | None) -> list[str]:
        if not value:
            return []
        separators = [";", "|"]
        parts = [value]
        for separator in separators:
            if separator in value:
                parts = value.split(separator)
                break
        return [part.strip() for part in parts if part.strip()]

    def _is_empty_row(self, raw_row: dict[object, object]) -> bool:
        return not any(_clean(value) for key, value in raw_row.items() if key is not None)
