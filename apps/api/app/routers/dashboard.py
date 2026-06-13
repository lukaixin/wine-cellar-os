from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Bottle, Cellar, InventoryTransaction, Location, Vintage, Wine
from app.routers.helpers import transaction_to_read
from app.schemas.common import DashboardSummary

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(session: Session = Depends(get_session)) -> dict:
    current_year = date.today().year
    total_bottles = session.scalar(select(func.count(Bottle.id))) or 0
    in_stock_bottles = session.scalar(select(func.count(Bottle.id)).where(Bottle.current_status == "in_stock")) or 0
    cellar_count = session.scalar(select(func.count(Cellar.id))) or 0
    location_count = session.scalar(select(func.count(Location.id))) or 0
    status_counts = dict(
        session.execute(select(Bottle.current_status, func.count(Bottle.id)).group_by(Bottle.current_status)).all()
    )
    recent_transactions = session.scalars(
        select(InventoryTransaction)
        .options(
            joinedload(InventoryTransaction.bottle).joinedload(Bottle.vintage).joinedload(Vintage.wine),
            joinedload(InventoryTransaction.from_location),
            joinedload(InventoryTransaction.to_location),
        )
        .order_by(InventoryTransaction.occurred_at.desc())
        .limit(8)
    ).all()
    in_stock_bottle_rows = session.scalars(
        select(Bottle)
        .options(joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer))
        .where(Bottle.current_status == "in_stock")
    ).all()
    drink_window_counts = {"entering": 0, "past": 0, "without": 0, "future": 0}
    inventory_by_country: dict[str, int] = {}
    inventory_by_type: dict[str, int] = {}
    for bottle in in_stock_bottle_rows:
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        country = (wine.country if wine else None) or (producer.country if producer else None) or "unknown"
        wine_type = (wine.type if wine else None) or "unknown"
        inventory_by_country[country] = inventory_by_country.get(country, 0) + 1
        inventory_by_type[wine_type] = inventory_by_type.get(wine_type, 0) + 1
        if not vintage or vintage.default_drink_from is None or vintage.default_drink_to is None:
            drink_window_counts["without"] += 1
        elif vintage.default_drink_to < current_year:
            drink_window_counts["past"] += 1
        elif vintage.default_drink_from <= current_year <= vintage.default_drink_to:
            drink_window_counts["entering"] += 1
        else:
            drink_window_counts["future"] += 1

    cellars = session.scalars(select(Cellar).options(joinedload(Cellar.locations))).unique().all()
    occupied_by_location: dict[str, int] = {}
    for bottle in in_stock_bottle_rows:
        if bottle.current_location_id:
            occupied_by_location[bottle.current_location_id] = occupied_by_location.get(bottle.current_location_id, 0) + 1
    cellar_occupancy = []
    for cellar in cellars:
        capacity = sum(location.capacity for location in cellar.locations)
        occupied = sum(occupied_by_location.get(location.id, 0) for location in cellar.locations)
        cellar_occupancy.append(
            {
                "cellar_id": cellar.id,
                "name": cellar.name,
                "capacity": capacity,
                "occupied": occupied,
                "empty": max(capacity - occupied, 0),
            }
        )
    return {
        "total_bottles": total_bottles,
        "in_stock_bottles": in_stock_bottles,
        "consumed_or_removed_bottles": total_bottles - in_stock_bottles,
        "cellar_count": cellar_count,
        "location_count": location_count,
        "recent_transactions": [transaction_to_read(transaction) for transaction in recent_transactions],
        "status_counts": status_counts,
        "drink_window_counts": drink_window_counts,
        "inventory_by_country": inventory_by_country,
        "inventory_by_type": inventory_by_type,
        "cellar_occupancy": cellar_occupancy,
    }
