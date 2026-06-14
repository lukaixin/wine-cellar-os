from __future__ import annotations

from typing import Any, TypeVar

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Bottle, InventoryTransaction, Location, Vintage, Wine
from app.services.drink_window_service import classify_vintage

T = TypeVar("T")


def get_or_404(session: Session, model: type[T], item_id: str, label: str) -> T:
    item = session.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return item


def commit_or_400(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc.orig)) from exc


def apply_update(item: Any, values: dict[str, Any]) -> None:
    for key, value in values.items():
        setattr(item, key, value)


def wine_to_read(wine: Wine) -> dict[str, Any]:
    return {
        "id": wine.id,
        "producer_id": wine.producer_id,
        "name_original": wine.name_original,
        "name_cn": wine.name_cn,
        "type": wine.type,
        "color": wine.color,
        "country": wine.country,
        "region": wine.region,
        "appellation": wine.appellation,
        "grape_varieties": wine.grape_varieties,
        "classification": wine.classification,
        "lwin7": wine.lwin7,
        "aliases": wine.aliases,
        "wine_identity_key": wine.wine_identity_key,
        "quality_status": wine.quality_status,
        "merged_into_id": wine.merged_into_id,
        "reviewed_at": wine.reviewed_at,
        "created_at": wine.created_at,
        "updated_at": wine.updated_at,
        "producer_name": wine.producer.name_original if wine.producer else None,
    }


def vintage_to_read(vintage: Vintage) -> dict[str, Any]:
    wine = vintage.wine
    producer = wine.producer if wine else None
    return {
        "id": vintage.id,
        "wine_id": vintage.wine_id,
        "vintage_year": vintage.vintage_year,
        "is_non_vintage": vintage.is_non_vintage,
        "lwin11": vintage.lwin11,
        "critic_score": vintage.critic_score,
        "critic_source": vintage.critic_source,
        "default_drink_from": vintage.default_drink_from,
        "default_drink_to": vintage.default_drink_to,
        "drink_window_confidence": vintage.drink_window_confidence,
        "notes": vintage.notes,
        "quality_status": vintage.quality_status,
        "reviewed_at": vintage.reviewed_at,
        "created_at": vintage.created_at,
        "updated_at": vintage.updated_at,
        "wine_name": wine.name_original if wine else None,
        "producer_name": producer.name_original if producer else None,
    }


def location_to_read(location: Location) -> dict[str, Any]:
    return {
        "id": location.id,
        "cellar_id": location.cellar_id,
        "code": location.code,
        "row_index": location.row_index,
        "column_index": location.column_index,
        "layer_index": location.layer_index,
        "position_note": location.position_note,
        "capacity": location.capacity,
        "location_type": location.location_type,
        "created_at": location.created_at,
        "updated_at": location.updated_at,
        "cellar_name": location.cellar.name if location.cellar else None,
    }


def bottle_to_read(bottle: Bottle) -> dict[str, Any]:
    vintage = bottle.vintage
    wine = vintage.wine if vintage else None
    producer = wine.producer if wine else None
    location = bottle.current_location
    cellar = location.cellar if location else None
    drink_window = classify_vintage(vintage)
    return {
        "id": bottle.id,
        "vintage_id": bottle.vintage_id,
        "bottle_size_ml": bottle.bottle_size_ml,
        "lwin16": bottle.lwin16,
        "acquisition_date": bottle.acquisition_date,
        "purchase_price": bottle.purchase_price,
        "purchase_currency": bottle.purchase_currency,
        "purchase_source": bottle.purchase_source,
        "purchase_channel": bottle.purchase_channel,
        "ws_price": bottle.ws_price,
        "condition": bottle.condition,
        "current_status": bottle.current_status,
        "current_location_id": bottle.current_location_id,
        "personal_rating": bottle.personal_rating,
        "personal_notes": bottle.personal_notes,
        "created_at": bottle.created_at,
        "updated_at": bottle.updated_at,
        "producer_name": producer.name_original if producer else None,
        "producer_name_cn": producer.name_cn if producer else None,
        "wine_name": wine.name_original if wine else None,
        "wine_name_cn": wine.name_cn if wine else None,
        "vintage_year": vintage.vintage_year if vintage else None,
        "is_non_vintage": vintage.is_non_vintage if vintage else None,
        "default_drink_from": vintage.default_drink_from if vintage else None,
        "default_drink_to": vintage.default_drink_to if vintage else None,
        "drink_window_confidence": vintage.drink_window_confidence if vintage else None,
        **drink_window.to_read_dict(),
        "wine_type": wine.type if wine else None,
        "country": wine.country or producer.country if wine and producer else (wine.country if wine else None),
        "cellar_name": cellar.name if cellar else None,
        "location_code": location.code if location else None,
    }


def transaction_to_read(transaction: InventoryTransaction) -> dict[str, Any]:
    bottle = transaction.bottle
    label = None
    if bottle and bottle.vintage and bottle.vintage.wine:
        year = "NV" if bottle.vintage.is_non_vintage else bottle.vintage.vintage_year
        label = f"{bottle.vintage.wine.name_original} {year}"
    return {
        "id": transaction.id,
        "bottle_id": transaction.bottle_id,
        "transaction_type": transaction.transaction_type,
        "from_location_id": transaction.from_location_id,
        "to_location_id": transaction.to_location_id,
        "occurred_at": transaction.occurred_at,
        "actor": transaction.actor,
        "reason": transaction.reason,
        "note": transaction.note,
        "created_at": transaction.created_at,
        "bottle_label": label,
        "from_location_code": transaction.from_location.code if transaction.from_location else None,
        "to_location_code": transaction.to_location.code if transaction.to_location else None,
    }
