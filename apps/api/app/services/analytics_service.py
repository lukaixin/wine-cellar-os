from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Bottle, InventoryTransaction, Location, Vintage, Wine
from app.models.base import utcnow

OUTBOUND_TYPES = {"CONSUME", "GIFT", "DAMAGE"}
ACTIVITY_TYPES = {"IN", "CONSUME", "GIFT", "MOVE", "DAMAGE"}


@dataclass(frozen=True)
class AnalyticsService:
    session: Session

    def summary(self, recent_limit: int = 20) -> dict[str, Any]:
        bottles = self.session.scalars(
            select(Bottle).options(
                joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer),
            )
        ).all()
        outbound_transactions = self.session.scalars(
            select(InventoryTransaction)
            .where(InventoryTransaction.transaction_type.in_(OUTBOUND_TYPES))
            .order_by(InventoryTransaction.occurred_at.asc(), InventoryTransaction.created_at.asc())
        ).all()
        recent_transactions = self.session.scalars(
            select(InventoryTransaction)
            .options(
                joinedload(InventoryTransaction.bottle).joinedload(Bottle.vintage).joinedload(Vintage.wine),
                joinedload(InventoryTransaction.from_location).joinedload(Location.cellar),
                joinedload(InventoryTransaction.to_location).joinedload(Location.cellar),
            )
            .where(InventoryTransaction.transaction_type.in_(ACTIVITY_TYPES))
            .order_by(InventoryTransaction.occurred_at.desc(), InventoryTransaction.created_at.desc())
            .limit(recent_limit)
        ).all()
        return {
            "inventory": self._inventory_summary(bottles),
            "consumption": self._consumption_summary(outbound_transactions),
            "activity": [self._activity_payload(transaction) for transaction in recent_transactions],
        }

    def _inventory_summary(self, bottles: list[Bottle]) -> dict[str, Any]:
        wine_ids: set[str] = set()
        producer_ids: set[str] = set()
        vintage_ids: set[str] = set()
        country_counts: Counter[str] = Counter()
        region_counts: Counter[str] = Counter()
        vintage_counts: Counter[str] = Counter()
        status_counts: Counter[str] = Counter()
        total_ws_value = Decimal("0.00")
        ws_priced_bottles = 0

        for bottle in bottles:
            vintage = bottle.vintage
            wine = vintage.wine if vintage else None
            producer = wine.producer if wine else None
            if wine:
                wine_ids.add(wine.id)
            if producer:
                producer_ids.add(producer.id)
            if vintage:
                vintage_ids.add(vintage.id)

            country_counts[(wine.country if wine else None) or (producer.country if producer else None) or "unknown"] += 1
            region_counts[(wine.region if wine else None) or (producer.region if producer else None) or "unknown"] += 1
            vintage_counts[self._vintage_label(vintage)] += 1
            status_counts[bottle.current_status] += 1
            if bottle.ws_price is not None:
                total_ws_value += bottle.ws_price
                ws_priced_bottles += 1

        return {
            "total_bottles": len(bottles),
            "total_wines": len(wine_ids),
            "total_producers": len(producer_ids),
            "total_vintages": len(vintage_ids),
            "total_ws_value": total_ws_value if ws_priced_bottles else None,
            "ws_priced_bottles": ws_priced_bottles,
            "country_distribution": self._distribution(country_counts),
            "region_distribution": self._distribution(region_counts),
            "vintage_distribution": self._distribution(vintage_counts),
            "status_distribution": self._distribution(status_counts),
        }

    def _consumption_summary(self, transactions: list[InventoryTransaction]) -> dict[str, Any]:
        now = utcnow()
        periods = [
            ("last_30_days", "Last 30 Days", now - timedelta(days=30)),
            ("last_90_days", "Last 90 Days", now - timedelta(days=90)),
            ("all_time", "All Time", None),
        ]
        period_payloads = []
        for key, label, threshold in periods:
            scoped = [item for item in transactions if threshold is None or self._occurred_after(item.occurred_at, threshold)]
            counts = Counter(item.transaction_type for item in scoped)
            period_payloads.append(
                {
                    "key": key,
                    "label": label,
                    "consumed_bottles": counts["CONSUME"],
                    "gifted_bottles": counts["GIFT"],
                    "damaged_bottles": counts["DAMAGE"],
                }
            )

        monthly_counts: dict[str, Counter[str]] = defaultdict(Counter)
        for transaction in transactions:
            month = transaction.occurred_at.strftime("%Y-%m")
            monthly_counts[month][transaction.transaction_type] += 1

        return {
            "periods": period_payloads,
            "monthly_trend": [
                {
                    "month": month,
                    "consumed_bottles": counts["CONSUME"],
                    "gifted_bottles": counts["GIFT"],
                    "damaged_bottles": counts["DAMAGE"],
                }
                for month, counts in sorted(monthly_counts.items())
            ],
        }

    def _activity_payload(self, transaction: InventoryTransaction) -> dict[str, Any]:
        return {
            "event_type": "IMPORT" if transaction.transaction_type == "IN" else transaction.transaction_type,
            "transaction_id": transaction.id,
            "bottle_id": transaction.bottle_id,
            "bottle_label": self._bottle_label(transaction.bottle),
            "occurred_at": transaction.occurred_at,
            "actor": transaction.actor,
            "reason": transaction.reason,
            "note": transaction.note,
            "from_location": self._location_payload(transaction.from_location),
            "to_location": self._location_payload(transaction.to_location),
        }

    def _distribution(self, counts: Counter[str]) -> list[dict[str, int | str]]:
        return [
            {"label": label, "count": count}
            for label, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _vintage_label(self, vintage: Vintage | None) -> str:
        if vintage is None:
            return "unknown"
        if vintage.is_non_vintage:
            return "NV"
        return str(vintage.vintage_year) if vintage.vintage_year is not None else "unknown"

    def _bottle_label(self, bottle: Bottle | None) -> str | None:
        if bottle is None or bottle.vintage is None or bottle.vintage.wine is None:
            return None
        vintage = bottle.vintage
        year = "NV" if vintage.is_non_vintage else str(vintage.vintage_year or "未知年份")
        return f"{vintage.wine.name_original} {year}"

    def _location_payload(self, location: Location | None) -> dict[str, str | None]:
        return {
            "id": location.id if location else None,
            "cellar_name": location.cellar.name if location and location.cellar else None,
            "code": location.code if location else None,
        }

    def _occurred_after(self, occurred_at: datetime, threshold: datetime) -> bool:
        if occurred_at.tzinfo is None and threshold.tzinfo is not None:
            threshold = threshold.replace(tzinfo=None)
        return occurred_at >= threshold
