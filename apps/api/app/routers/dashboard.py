from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_session
from app.models import Bottle, Cellar, InventoryTransaction, Location, Vintage, Wine
from app.routers.helpers import transaction_to_read
from app.schemas.common import DashboardSummary
from app.services.drink_window_service import DrinkWindowClassification, DrinkWindowStatus, classify_vintage

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(session: Session = Depends(get_session)) -> dict:
    today = date.today()
    total_bottles = session.scalar(select(func.count(Bottle.id))) or 0
    in_stock_bottles = session.scalar(select(func.count(Bottle.id)).where(Bottle.current_status == "in_stock")) or 0
    unavailable_bottles = total_bottles - in_stock_bottles
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
        .options(
            joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer),
            joinedload(Bottle.current_location).joinedload(Location.cellar),
        )
        .where(Bottle.current_status == "in_stock")
    ).all()

    drink_window_summary = {status.value: 0 for status in DrinkWindowStatus}
    inventory_by_country: dict[str, int] = {}
    inventory_by_type: dict[str, int] = {}
    upcoming_drink_candidates = []
    past_window_risks = []
    occupied_by_location: dict[str, int] = {}

    for bottle in in_stock_bottle_rows:
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        country = (wine.country if wine else None) or (producer.country if producer else None) or "unknown"
        wine_type = (wine.type if wine else None) or "unknown"
        inventory_by_country[country] = inventory_by_country.get(country, 0) + 1
        inventory_by_type[wine_type] = inventory_by_type.get(wine_type, 0) + 1
        if bottle.current_location_id:
            occupied_by_location[bottle.current_location_id] = occupied_by_location.get(bottle.current_location_id, 0) + 1

        classification = classify_vintage(vintage, today=today)
        drink_window_summary[classification.status.value] += 1
        insight = _bottle_insight(bottle, classification)
        if classification.status in {DrinkWindowStatus.ENTERING, DrinkWindowStatus.IN_WINDOW}:
            upcoming_drink_candidates.append(insight)
        elif classification.status in {DrinkWindowStatus.LATE, DrinkWindowStatus.PAST}:
            past_window_risks.append(insight)

    cellar_occupancy = _cellar_occupancy(session, occupied_by_location)
    drink_window_counts = _legacy_drink_window_counts(drink_window_summary)

    return {
        "total_bottles": total_bottles,
        "in_stock_bottles": in_stock_bottles,
        "available_bottles": in_stock_bottles,
        "consumed_or_removed_bottles": unavailable_bottles,
        "unavailable_bottles": unavailable_bottles,
        "cellar_count": cellar_count,
        "location_count": location_count,
        "recent_transactions": [transaction_to_read(transaction) for transaction in recent_transactions],
        "status_counts": status_counts,
        "drink_window_counts": drink_window_counts,
        "drink_window_summary": drink_window_summary,
        "upcoming_drink_candidates": sorted(
            upcoming_drink_candidates,
            key=lambda item: (
                0 if item["drink_window_status"] == DrinkWindowStatus.IN_WINDOW.value else 1,
                item["drink_to"] or 9999,
                item["bottle_label"],
            ),
        )[:8],
        "past_window_risks": sorted(
            past_window_risks,
            key=lambda item: (
                0 if item["drink_window_status"] == DrinkWindowStatus.PAST.value else 1,
                item["drink_to"] or 9999,
                item["bottle_label"],
            ),
        )[:8],
        "inventory_by_country": inventory_by_country,
        "inventory_by_type": inventory_by_type,
        "cellar_occupancy": cellar_occupancy,
        "cellar_health_score": _cellar_health_score(
            total_bottles=total_bottles,
            available_bottles=in_stock_bottles,
            unavailable_bottles=unavailable_bottles,
            drink_window_summary=drink_window_summary,
            cellar_occupancy=cellar_occupancy,
        ),
    }


def _legacy_drink_window_counts(drink_window_summary: dict[str, int]) -> dict[str, int]:
    return {
        "entering": drink_window_summary[DrinkWindowStatus.ENTERING.value]
        + drink_window_summary[DrinkWindowStatus.IN_WINDOW.value],
        "past": drink_window_summary[DrinkWindowStatus.LATE.value] + drink_window_summary[DrinkWindowStatus.PAST.value],
        "without": drink_window_summary[DrinkWindowStatus.UNKNOWN.value],
        "future": drink_window_summary[DrinkWindowStatus.TOO_EARLY.value],
    }


def _cellar_occupancy(session: Session, occupied_by_location: dict[str, int]) -> list[dict[str, int | str]]:
    cellars = session.scalars(select(Cellar).options(joinedload(Cellar.locations))).unique().all()
    result = []
    for cellar in cellars:
        capacity = sum(location.capacity for location in cellar.locations)
        occupied = sum(occupied_by_location.get(location.id, 0) for location in cellar.locations)
        result.append(
            {
                "cellar_id": cellar.id,
                "name": cellar.name,
                "capacity": capacity,
                "occupied": occupied,
                "empty": max(capacity - occupied, 0),
            }
        )
    return result


def _bottle_insight(bottle: Bottle, classification: DrinkWindowClassification) -> dict[str, str | int | bool | None]:
    vintage = bottle.vintage
    wine = vintage.wine if vintage else None
    producer = wine.producer if wine else None
    location = bottle.current_location
    cellar = location.cellar if location else None
    year = "NV" if vintage and vintage.is_non_vintage else str(vintage.vintage_year or "未知年份")
    wine_name = wine.name_original if wine else "未知酒款"
    producer_name = producer.name_original if producer else None
    bottle_label = f"{producer_name} · {wine_name} · {year}" if producer_name else f"{wine_name} · {year}"
    return {
        "bottle_id": bottle.id,
        "bottle_label": bottle_label,
        "producer_name": producer_name,
        "wine_name": wine.name_original if wine else None,
        "vintage_year": vintage.vintage_year if vintage else None,
        "is_non_vintage": vintage.is_non_vintage if vintage else None,
        "cellar_name": cellar.name if cellar else None,
        "location_code": location.code if location else None,
        "drink_from": classification.drink_from,
        "drink_to": classification.drink_to,
        "drink_window_status": classification.status.value,
        "drink_window_confidence": classification.confidence,
        "reason": classification.message,
    }


def _cellar_health_score(
    total_bottles: int,
    available_bottles: int,
    unavailable_bottles: int,
    drink_window_summary: dict[str, int],
    cellar_occupancy: list[dict[str, int | str]],
) -> dict:
    known_window_count = available_bottles - drink_window_summary[DrinkWindowStatus.UNKNOWN.value]
    coverage_score = round(known_window_count / available_bottles * 100) if available_bottles else 60
    coverage_factor = {
        "key": "drink_window_coverage",
        "label": "适饮期覆盖率",
        "score": _clamp_score(coverage_score),
        "detail": f"{known_window_count}/{available_bottles} 瓶在库酒有完整适饮期。",
    }

    overdue_count = drink_window_summary[DrinkWindowStatus.LATE.value] + drink_window_summary[DrinkWindowStatus.PAST.value]
    overdue_score = round(100 - overdue_count / available_bottles * 100) if available_bottles else 60
    overdue_factor = {
        "key": "overdue_risk",
        "label": "过期风险",
        "score": _clamp_score(overdue_score),
        "detail": f"{overdue_count} 瓶在库酒已晚于建议适饮期。",
    }

    total_capacity = sum(int(item["capacity"]) for item in cellar_occupancy)
    occupied = sum(int(item["occupied"]) for item in cellar_occupancy)
    if total_capacity <= 0:
        occupancy_score = 60
        occupancy_detail = "还没有可计算容量的酒柜位置。"
    else:
        occupancy_rate = occupied / total_capacity
        if occupancy_rate > 1:
            occupancy_score = 30
        elif occupancy_rate >= 0.95:
            occupancy_score = 55
        elif occupancy_rate >= 0.85:
            occupancy_score = 75
        else:
            occupancy_score = 100
        occupancy_detail = f"当前占用 {occupied}/{total_capacity}，约 {round(occupancy_rate * 100)}%。"
    occupancy_factor = {
        "key": "occupancy_pressure",
        "label": "酒柜容量压力",
        "score": _clamp_score(occupancy_score),
        "detail": occupancy_detail,
    }

    if total_bottles == 0:
        availability_score = 60
        availability_detail = "还没有库存数据。"
    elif available_bottles == 0:
        availability_score = 30
        availability_detail = "当前没有可用在库酒。"
    else:
        unavailable_ratio = unavailable_bottles / total_bottles
        availability_score = 65 if unavailable_ratio > 0.6 else 100
        availability_detail = f"{available_bottles} 瓶可用，{unavailable_bottles} 瓶已出库或不可用。"
    availability_factor = {
        "key": "availability_balance",
        "label": "可用库存平衡",
        "score": _clamp_score(availability_score),
        "detail": availability_detail,
    }

    factors = [coverage_factor, overdue_factor, occupancy_factor, availability_factor]
    score = round(
        coverage_factor["score"] * 0.35
        + overdue_factor["score"] * 0.35
        + occupancy_factor["score"] * 0.2
        + availability_factor["score"] * 0.1
    )
    score = _clamp_score(score)
    if score >= 85:
        label = "健康"
    elif score >= 70:
        label = "稳定"
    elif score >= 50:
        label = "需要关注"
    else:
        label = "风险较高"
    return {
        "score": score,
        "label": label,
        "factors": factors,
        "notes": ["该评分仅基于本地库存、位置容量和手工适饮期，不代表专业品鉴或投资建议。"],
    }


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))
