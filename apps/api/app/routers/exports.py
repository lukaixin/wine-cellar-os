from __future__ import annotations

import csv
from io import StringIO

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Bottle, Location, Vintage, Wine

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/bottles.csv")
def export_bottles_csv(session: Session = Depends(get_session)) -> Response:
    bottles = session.scalars(
        select(Bottle)
        .options(
            joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer),
            joinedload(Bottle.current_location).joinedload(Location.cellar),
        )
        .order_by(Bottle.created_at.desc())
    ).all()

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "bottle_id",
            "producer",
            "producer_cn",
            "wine",
            "wine_cn",
            "vintage_year",
            "is_non_vintage",
            "wine_type",
            "country",
            "status",
            "cellar",
            "location",
            "bottle_size_ml",
            "acquisition_date",
            "purchase_price",
            "purchase_currency",
            "purchase_source",
            "default_drink_from",
            "default_drink_to",
            "drink_window_confidence",
            "personal_notes",
        ]
    )
    for bottle in bottles:
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        location = bottle.current_location
        cellar = location.cellar if location else None
        writer.writerow(
            [
                bottle.id,
                producer.name_original if producer else "",
                producer.name_cn if producer else "",
                wine.name_original if wine else "",
                wine.name_cn if wine else "",
                vintage.vintage_year if vintage else "",
                vintage.is_non_vintage if vintage else "",
                wine.type if wine else "",
                (wine.country if wine else "") or (producer.country if producer else ""),
                bottle.current_status,
                cellar.name if cellar else "",
                location.code if location else "",
                bottle.bottle_size_ml,
                bottle.acquisition_date.isoformat() if bottle.acquisition_date else "",
                bottle.purchase_price if bottle.purchase_price is not None else "",
                bottle.purchase_currency,
                bottle.purchase_source or "",
                vintage.default_drink_from if vintage else "",
                vintage.default_drink_to if vintage else "",
                vintage.drink_window_confidence if vintage else "",
                bottle.personal_notes or "",
            ]
        )

    content = "\ufeff" + buffer.getvalue()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="wine-cellar-bottles.csv"'},
    )
