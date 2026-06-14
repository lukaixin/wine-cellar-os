from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Bottle, InventoryTransaction, Location, Producer, RegistryAlias, Vintage, Wine
from app.services.registry_service import RegistryService, normalize_registry_text


@dataclass(frozen=True)
class CollectionSearchFilters:
    query: str | None = None
    producer_id: str | None = None
    producer: str | None = None
    vintage_year: int | None = None
    location_id: str | None = None
    location: str | None = None
    status: str | None = None
    limit: int = 25
    offset: int = 0


@dataclass(frozen=True)
class CollectionService:
    session: Session

    def search(self, filters: CollectionSearchFilters) -> dict[str, Any]:
        bottles = self.session.scalars(
            select(Bottle)
            .options(
                joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer),
                joinedload(Bottle.current_location).joinedload(Location.cellar),
            )
            .order_by(Bottle.created_at.desc(), Bottle.id.asc())
        ).all()
        matched_entities = self._matched_entity_ids(filters.query)
        filtered = [bottle for bottle in bottles if self._matches_filters(bottle, filters, matched_entities)]
        grouped = self._group_results(filtered)
        total = len(grouped)
        return {
            "query": filters.query,
            "total": total,
            "limit": filters.limit,
            "offset": filters.offset,
            "items": grouped[filters.offset : filters.offset + filters.limit],
        }

    def bottle_detail(self, bottle_id: str) -> dict[str, Any] | None:
        bottle = self.session.scalar(
            select(Bottle)
            .options(
                joinedload(Bottle.vintage).joinedload(Vintage.wine).joinedload(Wine.producer),
                joinedload(Bottle.current_location).joinedload(Location.cellar),
            )
            .where(Bottle.id == bottle_id)
        )
        if bottle is None:
            return None
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        return {
            "id": bottle.id,
            "bottle_id": bottle.id,
            "bottle_size_ml": bottle.bottle_size_ml,
            "quantity": 1,
            "status": bottle.current_status,
            "ws_price": bottle.ws_price,
            "acquisition_date": bottle.acquisition_date,
            "vintage_id": bottle.vintage_id,
            "vintage_year": vintage.vintage_year if vintage else None,
            "is_non_vintage": vintage.is_non_vintage if vintage else False,
            "wine_id": wine.id if wine else None,
            "wine_name": wine.name_original if wine else None,
            "wine_name_cn": wine.name_cn if wine else None,
            "producer_id": producer.id if producer else None,
            "producer_name": producer.name_original if producer else None,
            "producer_name_cn": producer.name_cn if producer else None,
            "location": self._location_payload(bottle.current_location),
            "created_at": bottle.created_at,
            "updated_at": bottle.updated_at,
        }

    def bottle_timeline(self, bottle_id: str) -> list[dict[str, Any]] | None:
        bottle_exists = self.session.scalar(select(Bottle.id).where(Bottle.id == bottle_id))
        if bottle_exists is None:
            return None
        transactions = self.session.scalars(
            select(InventoryTransaction)
            .options(
                joinedload(InventoryTransaction.from_location),
                joinedload(InventoryTransaction.to_location),
            )
            .where(InventoryTransaction.bottle_id == bottle_id)
            .order_by(InventoryTransaction.occurred_at.desc(), InventoryTransaction.created_at.desc())
        ).all()
        return [self._timeline_payload(transaction) for transaction in transactions]

    def _matches_filters(
        self,
        bottle: Bottle,
        filters: CollectionSearchFilters,
        matched_entities: dict[str, set[str]] | None,
    ) -> bool:
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        location = bottle.current_location
        if filters.status and bottle.current_status != filters.status:
            return False
        if filters.producer_id and (not producer or producer.id != filters.producer_id):
            return False
        if filters.producer and normalize_registry_text(filters.producer) not in {
            normalize_registry_text(producer.name_original if producer else None),
            normalize_registry_text(producer.name_cn if producer else None),
        }:
            return False
        if filters.vintage_year is not None and (not vintage or vintage.vintage_year != filters.vintage_year):
            return False
        if filters.location_id and bottle.current_location_id != filters.location_id:
            return False
        if filters.location:
            location_key = normalize_registry_text(filters.location)
            location_values = {
                normalize_registry_text(location.code if location else None),
                normalize_registry_text(location.cellar.name if location and location.cellar else None),
            }
            if location_key not in location_values:
                return False
        if matched_entities is None:
            return True
        if vintage and vintage.id in matched_entities["vintage_ids"]:
            return True
        if wine and wine.id in matched_entities["wine_ids"]:
            return True
        if producer and producer.id in matched_entities["producer_ids"]:
            return True
        return self._matches_query_text(bottle, matched_entities["query_key"])

    def _matched_entity_ids(self, query: str | None) -> dict[str, set[str]] | None:
        query_key = normalize_registry_text(query)
        if not query_key:
            return None
        results = RegistryService(self.session).search(query or "", limit_per_type=500)
        return {
            "query_key": {query_key},
            "producer_ids": {item["id"] for item in results["producers"]},
            "wine_ids": {item["id"] for item in results["wines"]},
            "vintage_ids": {item["id"] for item in results["vintages"]},
        }

    def _matches_query_text(self, bottle: Bottle, query_keys: set[str]) -> bool:
        query_key = next(iter(query_keys))
        tokens = [token for token in query_key.split(" ") if token]
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        values = [
            producer.name_original if producer else None,
            producer.name_cn if producer else None,
            wine.name_original if wine else None,
            wine.name_cn if wine else None,
            "NV" if vintage and vintage.is_non_vintage else vintage.vintage_year if vintage else None,
        ]
        values.extend(self._alias_texts(producer, wine, vintage))
        haystack = normalize_registry_text(" ".join(str(value) for value in values if value is not None))
        if query_key in haystack:
            return True
        return bool(tokens) and all(token in haystack for token in tokens)

    def _alias_texts(self, producer: Producer | None, wine: Wine | None, vintage: Vintage | None) -> list[str]:
        entity_pairs = [
            ("producer", producer.id if producer else None, producer.aliases if producer else None),
            ("wine", wine.id if wine else None, wine.aliases if wine else None),
            ("vintage", vintage.id if vintage else None, None),
        ]
        texts: list[str] = []
        for entity_type, entity_id, embedded_aliases in entity_pairs:
            if entity_id:
                aliases = self.session.scalars(
                    select(RegistryAlias).where(
                        RegistryAlias.entity_type == entity_type,
                        RegistryAlias.entity_id == entity_id,
                        RegistryAlias.status != "rejected",
                    )
                ).all()
                texts.extend(alias.alias_text for alias in aliases)
            texts.extend(self._flatten_aliases(embedded_aliases))
        return texts

    def _group_results(self, bottles: list[Bottle]) -> list[dict[str, Any]]:
        groups: dict[tuple[str, str | None, str], list[Bottle]] = {}
        for bottle in bottles:
            groups.setdefault((bottle.vintage_id, bottle.current_location_id, bottle.current_status), []).append(bottle)

        rows = [self._group_payload(items) for items in groups.values()]
        return sorted(
            rows,
            key=lambda item: (
                item["producer_name"] or "",
                item["wine_name"] or "",
                -(item["vintage_year"] or 0),
                item["location"]["cellar_name"] or "",
                item["location"]["code"] or "",
                item["status"],
            ),
        )

    def _group_payload(self, bottles: list[Bottle]) -> dict[str, Any]:
        ordered = sorted(bottles, key=lambda item: (item.created_at, item.id), reverse=True)
        bottle = ordered[0]
        vintage = bottle.vintage
        wine = vintage.wine if vintage else None
        producer = wine.producer if wine else None
        return {
            "bottle_id": bottle.id,
            "bottle_ids": [item.id for item in ordered],
            "producer_id": producer.id if producer else None,
            "producer_name": producer.name_original if producer else None,
            "producer_name_cn": producer.name_cn if producer else None,
            "wine_id": wine.id if wine else None,
            "wine_name": wine.name_original if wine else None,
            "wine_name_cn": wine.name_cn if wine else None,
            "vintage_id": bottle.vintage_id,
            "vintage_year": vintage.vintage_year if vintage else None,
            "is_non_vintage": vintage.is_non_vintage if vintage else False,
            "bottle_count": len(ordered),
            "location": self._location_payload(bottle.current_location),
            "status": bottle.current_status,
        }

    def _location_payload(self, location: Location | None) -> dict[str, str | None]:
        return {
            "id": location.id if location else None,
            "cellar_name": location.cellar.name if location and location.cellar else None,
            "code": location.code if location else None,
        }

    def _timeline_payload(self, transaction: InventoryTransaction) -> dict[str, Any]:
        return {
            "event_type": transaction.transaction_type,
            "event_time": transaction.occurred_at,
            "quantity_delta": self._quantity_delta(transaction.transaction_type),
            "reference_type": "inventory_transaction",
            "reference_id": transaction.id,
            "from_location": self._location_payload(transaction.from_location),
            "to_location": self._location_payload(transaction.to_location),
            "notes": self._timeline_notes(transaction),
        }

    def _quantity_delta(self, transaction_type: str) -> int:
        if transaction_type == "IN":
            return 1
        if transaction_type in {"CONSUME", "GIFT", "DAMAGE"}:
            return -1
        return 0

    def _timeline_notes(self, transaction: InventoryTransaction) -> str | None:
        values = [value for value in (transaction.reason, transaction.note) if value]
        return " · ".join(values) if values else None

    def _flatten_aliases(self, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            aliases: list[str] = []
            for item in value.values():
                aliases.extend(self._flatten_aliases(item))
            return aliases
        if isinstance(value, list | tuple | set):
            aliases: list[str] = []
            for item in value:
                aliases.extend(self._flatten_aliases(item))
            return aliases
        return []
