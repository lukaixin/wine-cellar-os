from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models import (
    Bottle,
    ImportMapping,
    Producer,
    RegistryAlias,
    RegistryQualityFinding,
    RegistryReviewQueue,
    Vintage,
    Wine,
)

RULE_VERSION = "registry-v1"
AliasStatus = Literal["observed", "candidate", "approved", "rejected", "conflict"]
ImportDecision = Literal["auto_accepted", "needs_review", "manual_required", "rejected"]

QUALITY_SCORE_ADJUSTMENTS = {
    "approved": 4,
    "reviewed": 2,
    "unreviewed": 0,
    "needs_review": -5,
    "conflict": -10,
    "rejected": -20,
}

SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


_PUNCT_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "`": "'",
        "´": "'",
        "“": '"',
        "”": '"',
        "‐": "-",
        "‑": "-",
        "–": "-",
        "—": "-",
        "－": "-",
        "·": " ",
        "•": " ",
        "，": ",",
        "。": ".",
        "：": ":",
        "；": ";",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
    }
)


def normalize_registry_text(value: object) -> str:
    if value is None:
        return ""
    text = unicodedata.normalize("NFKC", str(value)).translate(_PUNCT_TRANSLATION).strip().casefold()
    text = "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))
    text = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_producer_canonical_key(producer_name: str | None, producer_name_cn: str | None = None) -> str:
    return normalize_registry_text(producer_name or producer_name_cn or "unknown producer")


def build_wine_identity_key(
    producer_key: str | None,
    wine_name: str | None,
    *,
    country: str | None = None,
    region: str | None = None,
    appellation: str | None = None,
    wine_type: str | None = None,
) -> str:
    producer_part = producer_key or "unknown producer"
    parts = [
        producer_part,
        normalize_registry_text(wine_name or "unknown wine"),
        normalize_registry_text(country),
        normalize_registry_text(region),
        normalize_registry_text(appellation),
        normalize_registry_text(wine_type),
    ]
    return " | ".join(part for part in parts if part)


def decision_from_score(score: int) -> ImportDecision:
    if score >= 95:
        return "auto_accepted"
    if score >= 80:
        return "needs_review"
    return "manual_required"


def quality_adjusted_score(score: int, quality_status: str | None) -> int:
    adjustment = QUALITY_SCORE_ADJUSTMENTS.get(quality_status or "unreviewed", -2)
    return max(0, min(100, score + adjustment))


def vintage_display_name(vintage: Vintage) -> str:
    wine = vintage.wine
    producer = wine.producer if wine else None
    year = "NV" if vintage.is_non_vintage else str(vintage.vintage_year or "未知年份")
    if producer and wine:
        return f"{producer.name_original} · {wine.name_original} · {year}"
    if wine:
        return f"{wine.name_original} · {year}"
    return year


@dataclass(frozen=True)
class RegistryMatch:
    entity_type: str
    target_id: str | None
    match_score: int
    decision: ImportDecision
    matched_by: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WineListRegistryDecision:
    producer_match: RegistryMatch
    wine_match: RegistryMatch
    vintage_match: RegistryMatch

    @property
    def overall_match_score(self) -> int:
        return min(
            self.producer_match.match_score,
            self.wine_match.match_score,
            self.vintage_match.match_score,
        )

    @property
    def decision(self) -> ImportDecision:
        decisions = {self.producer_match.decision, self.wine_match.decision, self.vintage_match.decision}
        if "manual_required" in decisions:
            return "manual_required"
        if "needs_review" in decisions:
            return "needs_review"
        return "auto_accepted"


@dataclass(frozen=True)
class RegistryService:
    session: Session

    def apply_producer_fields(self, producer: Producer) -> None:
        producer.canonical_key = build_producer_canonical_key(producer.name_original, producer.name_cn)
        producer.quality_status = producer.quality_status or "unreviewed"

    def apply_wine_fields(self, wine: Wine, producer: Producer | None = None) -> None:
        producer = producer or self.session.get(Producer, wine.producer_id)
        producer_key = producer.canonical_key if producer else None
        if producer is not None and not producer_key:
            self.apply_producer_fields(producer)
            producer_key = producer.canonical_key
        wine.wine_identity_key = build_wine_identity_key(
            producer_key,
            wine.name_original,
            country=wine.country,
            region=wine.region,
            appellation=wine.appellation,
            wine_type=wine.type,
        )
        wine.quality_status = wine.quality_status or "unreviewed"

    def apply_vintage_fields(self, vintage: Vintage) -> None:
        vintage.quality_status = vintage.quality_status or "unreviewed"

    def apply_registry_fields(self, producer: Producer | None = None, wine: Wine | None = None, vintage: Vintage | None = None) -> None:
        if producer is not None:
            self.apply_producer_fields(producer)
        if wine is not None:
            self.apply_wine_fields(wine)
        if vintage is not None:
            self.apply_vintage_fields(vintage)

    def evaluate_winelist_row(
        self,
        *,
        producer_name: str,
        wine_name: str,
        vintage_year: int,
        country: str | None,
        region: str | None,
        appellation: str | None,
        wine_type: str | None,
    ) -> WineListRegistryDecision:
        producer_match = self.match_producer(producer_name)
        producer = self.session.get(Producer, producer_match.target_id) if producer_match.target_id else None
        wine_match = self.match_wine(
            producer,
            wine_name,
            country=country,
            region=region,
            appellation=appellation,
            wine_type=wine_type,
        )
        wine = self.session.get(Wine, wine_match.target_id) if wine_match.target_id else None
        vintage_match = self.match_vintage(wine, vintage_year)
        return WineListRegistryDecision(
            producer_match=producer_match,
            wine_match=wine_match,
            vintage_match=vintage_match,
        )

    def match_producer(self, producer_name: str) -> RegistryMatch:
        raw_key = normalize_registry_text(producer_name)
        producers = self.session.scalars(select(Producer)).all()
        if not producers:
            return RegistryMatch("producer", None, 100, "auto_accepted", "new_entity", {"canonical_key": raw_key})

        for producer in producers:
            if not producer.canonical_key:
                self.apply_producer_fields(producer)
            if producer.canonical_key == raw_key:
                return RegistryMatch("producer", producer.id, 100, "auto_accepted", "canonical_key", {"canonical_key": raw_key})

        approved_alias_owner = self._approved_alias_owner("producer", raw_key)
        if approved_alias_owner == "conflict":
            return RegistryMatch("producer", None, 90, "needs_review", "alias_conflict", {"alias_key": raw_key})
        if isinstance(approved_alias_owner, str):
            return RegistryMatch("producer", approved_alias_owner, 100, "auto_accepted", "approved_alias", {"alias_key": raw_key})

        best = self._best_score(
            raw_key,
            [(producer.id, producer.canonical_key or build_producer_canonical_key(producer.name_original, producer.name_cn)) for producer in producers],
        )
        if best is None:
            return RegistryMatch("producer", None, 100, "auto_accepted", "new_entity", {"canonical_key": raw_key})
        target_id, target_key, score = best
        return RegistryMatch(
            "producer",
            target_id if score >= 80 else None,
            score,
            decision_from_score(score),
            "fuzzy_key",
            {"canonical_key": raw_key, "candidate_key": target_key},
        )

    def match_wine(
        self,
        producer: Producer | None,
        wine_name: str,
        *,
        country: str | None,
        region: str | None,
        appellation: str | None,
        wine_type: str | None,
    ) -> RegistryMatch:
        wine_key = normalize_registry_text(wine_name)
        if producer is None:
            return RegistryMatch("wine", None, 100, "auto_accepted", "new_entity", {"wine_key": wine_key})

        if not producer.canonical_key:
            self.apply_producer_fields(producer)
        identity_key = build_wine_identity_key(
            producer.canonical_key,
            wine_name,
            country=country,
            region=region,
            appellation=appellation,
            wine_type=wine_type,
        )
        wines = self.session.scalars(select(Wine).where(Wine.producer_id == producer.id)).all()
        if not wines:
            return RegistryMatch("wine", None, 100, "auto_accepted", "new_entity", {"wine_identity_key": identity_key})

        for wine in wines:
            if not wine.wine_identity_key:
                self.apply_wine_fields(wine, producer)
            if wine.wine_identity_key == identity_key or normalize_registry_text(wine.name_original) == wine_key:
                return RegistryMatch(
                    "wine",
                    wine.id,
                    100,
                    "auto_accepted",
                    "wine_identity_key",
                    {"wine_identity_key": identity_key},
                )

        approved_alias_owner = self._approved_alias_owner("wine", wine_key)
        if approved_alias_owner == "conflict":
            return RegistryMatch("wine", None, 90, "needs_review", "alias_conflict", {"alias_key": wine_key})
        if isinstance(approved_alias_owner, str) and any(wine.id == approved_alias_owner for wine in wines):
            return RegistryMatch("wine", approved_alias_owner, 100, "auto_accepted", "approved_alias", {"alias_key": wine_key})

        candidates = [(wine.id, normalize_registry_text(wine.name_original)) for wine in wines]
        best = self._best_score(wine_key, candidates)
        if best is None:
            return RegistryMatch("wine", None, 100, "auto_accepted", "new_entity", {"wine_identity_key": identity_key})
        target_id, target_key, score = best
        return RegistryMatch(
            "wine",
            target_id if score >= 80 else None,
            score,
            decision_from_score(score),
            "fuzzy_key",
            {"wine_identity_key": identity_key, "candidate_key": target_key},
        )

    def match_vintage(self, wine: Wine | None, vintage_year: int) -> RegistryMatch:
        if wine is None:
            return RegistryMatch("vintage", None, 100, "auto_accepted", "new_entity", {"vintage_year": vintage_year})
        vintage = self.session.scalar(
            select(Vintage).where(
                Vintage.wine_id == wine.id,
                Vintage.vintage_year == vintage_year,
                Vintage.is_non_vintage.is_(False),
            )
        )
        if vintage is not None:
            return RegistryMatch("vintage", vintage.id, 100, "auto_accepted", "exact_year", {"vintage_year": vintage_year})
        return RegistryMatch("vintage", None, 100, "auto_accepted", "new_entity", {"vintage_year": vintage_year})

    def search(self, query: str, *, limit_per_type: int = 10) -> dict[str, Any]:
        query_key = normalize_registry_text(query)
        if not query_key:
            return {"query": query, "producers": [], "wines": [], "vintages": []}

        aliases = self._search_aliases()
        producers = self.session.scalars(select(Producer).order_by(Producer.name_original)).all()
        wines = self.session.scalars(
            select(Wine).options(joinedload(Wine.producer)).order_by(Wine.name_original)
        ).all()
        vintages = self.session.scalars(
            select(Vintage).options(joinedload(Vintage.wine).joinedload(Wine.producer))
        ).all()

        return {
            "query": query,
            "producers": self._top_results(
                [
                    self._producer_search_result(producer, query_key, aliases.get(("producer", producer.id), []))
                    for producer in producers
                ],
                limit_per_type,
            ),
            "wines": self._top_results(
                [self._wine_search_result(wine, query_key, self._wine_alias_candidates(wine, aliases)) for wine in wines],
                limit_per_type,
            ),
            "vintages": self._top_results(
                [
                    self._vintage_search_result(
                        vintage,
                        query_key,
                        self._vintage_alias_candidates(vintage, aliases),
                    )
                    for vintage in vintages
                ],
                limit_per_type,
            ),
        }

    def producer_detail(self, producer_id: str) -> dict[str, Any] | None:
        producer = self.session.get(Producer, producer_id)
        if producer is None:
            return None
        if not producer.canonical_key:
            self.apply_producer_fields(producer)
        wine_count = self.session.scalar(select(func.count(Wine.id)).where(Wine.producer_id == producer.id)) or 0
        return {
            "id": producer.id,
            "entity_type": "producer",
            "canonical_name": producer.name_original,
            "name_cn": producer.name_cn,
            "aliases": self._entity_alias_texts("producer", producer.id, producer.aliases),
            "country": producer.country,
            "region": producer.region,
            "wine_count": wine_count,
            "quality_status": producer.quality_status,
            "canonical_key": producer.canonical_key,
        }

    def wine_detail(self, wine_id: str) -> dict[str, Any] | None:
        wine = self.session.scalar(
            select(Wine).options(joinedload(Wine.producer)).where(Wine.id == wine_id)
        )
        if wine is None:
            return None
        if not wine.wine_identity_key:
            self.apply_wine_fields(wine, wine.producer)
        vintage_count = self.session.scalar(select(func.count(Vintage.id)).where(Vintage.wine_id == wine.id)) or 0
        producer_name = wine.producer.name_original if wine.producer else "未知酒庄"
        return {
            "id": wine.id,
            "entity_type": "wine",
            "canonical_name": wine.name_original,
            "name_cn": wine.name_cn,
            "producer_id": wine.producer_id,
            "producer_name": producer_name,
            "aliases": self._entity_alias_texts("wine", wine.id, wine.aliases),
            "vintage_count": vintage_count,
            "quality_status": wine.quality_status,
            "wine_identity_key": wine.wine_identity_key,
        }

    def vintage_detail(self, vintage_id: str) -> dict[str, Any] | None:
        vintage = self.session.execute(
            select(Vintage)
            .options(joinedload(Vintage.wine).joinedload(Wine.producer), joinedload(Vintage.drink_windows))
            .where(Vintage.id == vintage_id)
        ).unique().scalar_one_or_none()
        if vintage is None:
            return None
        bottle_count = self.session.scalar(select(func.count(Bottle.id)).where(Bottle.vintage_id == vintage.id)) or 0
        wine = vintage.wine
        producer = wine.producer if wine else None
        return {
            "id": vintage.id,
            "entity_type": "vintage",
            "producer_id": producer.id if producer else "",
            "producer_name": producer.name_original if producer else "未知酒庄",
            "wine_id": wine.id if wine else "",
            "wine_name": wine.name_original if wine else "未知酒款",
            "vintage_year": vintage.vintage_year,
            "is_non_vintage": vintage.is_non_vintage,
            "bottle_count": bottle_count,
            "default_drink_from": vintage.default_drink_from,
            "default_drink_to": vintage.default_drink_to,
            "drink_window_confidence": vintage.drink_window_confidence,
            "drink_windows": [
                {
                    "source": window.source,
                    "source_detail": window.source_detail,
                    "drink_from": window.drink_from,
                    "drink_to": window.drink_to,
                    "peak_from": window.peak_from,
                    "peak_to": window.peak_to,
                    "confidence": window.confidence,
                    "notes": window.notes,
                }
                for window in sorted(vintage.drink_windows, key=lambda item: item.created_at, reverse=True)
            ],
            "quality_status": vintage.quality_status,
        }

    def discovery(self, *, limit_per_type: int = 5, risk_limit: int = 10) -> dict[str, Any]:
        self.ensure_quality_findings()
        producers = self.session.scalars(
            select(Producer).order_by(Producer.created_at.desc(), Producer.name_original.asc()).limit(limit_per_type)
        ).all()
        wines = self.session.scalars(
            select(Wine)
            .options(joinedload(Wine.producer))
            .order_by(Wine.created_at.desc(), Wine.name_original.asc())
            .limit(limit_per_type)
        ).all()
        vintages = self.session.scalars(
            select(Vintage)
            .options(joinedload(Vintage.wine).joinedload(Wine.producer))
            .order_by(Vintage.created_at.desc(), Vintage.vintage_year.desc().nullslast())
            .limit(limit_per_type)
        ).all()
        risks = self.session.scalars(
            select(RegistryQualityFinding)
            .where(
                RegistryQualityFinding.status == "open",
                RegistryQualityFinding.finding_type.in_(["alias_conflict", "duplicate_producer", "duplicate_wine"]),
            )
            .order_by(RegistryQualityFinding.created_at.desc(), RegistryQualityFinding.id.desc())
            .limit(risk_limit * 3)
        ).all()
        risks = sorted(risks, key=lambda item: (SEVERITY_RANK.get(item.severity, 9), item.created_at), reverse=False)[
            :risk_limit
        ]
        return {
            "recent_producers": [
                {
                    "id": producer.id,
                    "entity_type": "producer",
                    "display_name": producer.name_original,
                    "created_at": producer.created_at,
                    "quality_status": producer.quality_status,
                }
                for producer in producers
            ],
            "recent_wines": [
                {
                    "id": wine.id,
                    "entity_type": "wine",
                    "display_name": self._wine_display_name(wine),
                    "created_at": wine.created_at,
                    "quality_status": wine.quality_status,
                }
                for wine in wines
            ],
            "recent_vintages": [
                {
                    "id": vintage.id,
                    "entity_type": "vintage",
                    "display_name": vintage_display_name(vintage),
                    "created_at": vintage.created_at,
                    "quality_status": vintage.quality_status,
                }
                for vintage in vintages
            ],
            "quality_risks": [
                {
                    "id": risk.id,
                    "finding_type": risk.finding_type,
                    "severity": risk.severity,
                    "entity_type": risk.entity_type,
                    "entity_id": risk.entity_id,
                    "suggested_action": risk.suggested_action,
                    "evidence": risk.evidence,
                    "created_at": risk.created_at,
                }
                for risk in risks
            ],
        }

    def record_import_mapping(
        self,
        *,
        source: str,
        import_batch_id: str | None,
        import_batch_row_id: str | None,
        source_row_number: int | None,
        raw_value: dict[str, Any] | str | None,
        match: RegistryMatch,
    ) -> ImportMapping:
        mapping = ImportMapping(
            source=source,
            import_batch_id=import_batch_id,
            import_batch_row_id=import_batch_row_id,
            source_row_number=source_row_number,
            raw_value=raw_value,
            target_entity_type=match.entity_type,
            target_entity_id=match.target_id,
            match_score=match.match_score,
            decision=match.decision,
            rule_version=RULE_VERSION,
            evidence={"matched_by": match.matched_by, **match.evidence},
        )
        self.session.add(mapping)
        self.session.flush()
        return mapping

    def enqueue_review(
        self,
        *,
        review_type: str,
        title: str,
        detail: str | None = None,
        source: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        import_mapping_id: str | None = None,
        raw_value: dict[str, Any] | str | None = None,
        match_score: int | None = None,
        evidence: dict[str, Any] | list[Any] | None = None,
    ) -> RegistryReviewQueue:
        item = RegistryReviewQueue(
            review_type=review_type,
            status="open",
            source=source,
            entity_type=entity_type,
            entity_id=entity_id,
            import_mapping_id=import_mapping_id,
            raw_value=raw_value,
            match_score=match_score,
            title=title,
            detail=detail,
            evidence=evidence,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def record_alias(
        self,
        *,
        entity_type: str,
        entity_id: str,
        alias_text: str,
        status: AliasStatus = "observed",
        source: str | None = None,
        import_mapping_id: str | None = None,
        confidence: str | None = None,
        note: str | None = None,
    ) -> RegistryAlias:
        alias_key = normalize_registry_text(alias_text)
        final_status: AliasStatus = status
        conflict = self._alias_conflict(entity_type, alias_key, entity_id)
        if conflict:
            final_status = "conflict"
        alias = RegistryAlias(
            entity_type=entity_type,
            entity_id=entity_id,
            alias_text=alias_text,
            alias_key=alias_key,
            status=final_status,
            source=source,
            rule_version=RULE_VERSION,
            confidence=confidence,
            import_mapping_id=import_mapping_id,
            note=note,
        )
        self.session.add(alias)
        self.session.flush()
        if conflict:
            self.enqueue_review(
                review_type="alias_conflict",
                title=f"Alias conflict: {alias_text}",
                detail=f"{entity_type} alias is already approved for another registry entity.",
                source=source,
                entity_type=entity_type,
                entity_id=entity_id,
                import_mapping_id=import_mapping_id,
                raw_value=alias_text,
                match_score=90,
                evidence={"alias_key": alias_key, "conflicting_entity_ids": sorted(conflict)},
            )
        return alias

    def ensure_quality_findings(self) -> None:
        existing_hashes = set(self.session.scalars(select(RegistryQualityFinding.evidence_hash)).all())
        for finding in self._generate_quality_findings():
            if finding["evidence_hash"] in existing_hashes:
                continue
            self.session.add(RegistryQualityFinding(**finding))
            existing_hashes.add(finding["evidence_hash"])
        self.session.flush()

    def _generate_quality_findings(self) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        producers = self.session.scalars(select(Producer)).all()
        wines = self.session.scalars(select(Wine).options(joinedload(Wine.producer))).all()
        vintages = self.session.scalars(select(Vintage).options(joinedload(Vintage.wine))).all()

        for producer in producers:
            if not producer.canonical_key:
                self.apply_producer_fields(producer)
            if not producer.country:
                findings.append(
                    self._finding(
                        "missing_country",
                        "low",
                        "producer",
                        producer.id,
                        {"producer": producer.name_original},
                        "补充国家，若来源不明确则保持 manual/low confidence 标记。",
                    )
                )
            if not producer.region:
                findings.append(
                    self._finding(
                        "missing_region",
                        "low",
                        "producer",
                        producer.id,
                        {"producer": producer.name_original},
                        "补充产区，若来源不明确则保留 unknown/manual 语义。",
                    )
                )

        for key, group in self._group_by_key(producers, lambda item: item.canonical_key).items():
            if key and len(group) > 1:
                findings.append(
                    self._finding(
                        "duplicate_producer",
                        "high",
                        "producer",
                        group[0].id,
                        {"canonical_key": key, "producer_ids": [item.id for item in group]},
                        "人工确认是否需要设置 merged_into_id；不要自动合并历史数据。",
                    )
                )
                self._enqueue_missing_queue_once(
                    "suspected_duplicate",
                    f"疑似重复酒庄: {key}",
                    "duplicate_producer",
                    "producer",
                    group[0].id,
                    {"producer_ids": [item.id for item in group]},
                )

        for wine in wines:
            if not wine.wine_identity_key:
                self.apply_wine_fields(wine, wine.producer)
            if not wine.country:
                findings.append(
                    self._finding(
                        "missing_country",
                        "low",
                        "wine",
                        wine.id,
                        {"wine": wine.name_original, "producer": wine.producer.name_original if wine.producer else None},
                        "补充酒款国家，优先来自导入表或人工确认。",
                    )
                )
            if not wine.region:
                findings.append(
                    self._finding(
                        "missing_region",
                        "low",
                        "wine",
                        wine.id,
                        {"wine": wine.name_original, "producer": wine.producer.name_original if wine.producer else None},
                        "补充酒款产区，低置信来源不要伪装成权威字段。",
                    )
                )
            if not wine.vintages:
                findings.append(
                    self._finding(
                        "missing_vintage",
                        "medium",
                        "wine",
                        wine.id,
                        {"wine": wine.name_original, "producer": wine.producer.name_original if wine.producer else None},
                        "补充 Vintage 或确认该酒款暂未入库具体年份。",
                    )
                )

        for key, group in self._group_by_key(wines, lambda item: item.wine_identity_key).items():
            if key and len(group) > 1:
                findings.append(
                    self._finding(
                        "duplicate_wine",
                        "high",
                        "wine",
                        group[0].id,
                        {"wine_identity_key": key, "wine_ids": [item.id for item in group]},
                        "人工确认是否同款；不迁移 Bottle 外键，不自动合并。",
                    )
                )
                self._enqueue_missing_queue_once(
                    "suspected_duplicate",
                    f"疑似重复酒款: {key}",
                    "duplicate_wine",
                    "wine",
                    group[0].id,
                    {"wine_ids": [item.id for item in group]},
                )

        for vintage in vintages:
            if vintage.default_drink_from is None or vintage.default_drink_to is None:
                findings.append(
                    self._finding(
                        "missing_drink_window",
                        "medium",
                        "vintage",
                        vintage.id,
                        {
                            "wine": vintage.wine.name_original if vintage.wine else None,
                            "vintage_year": vintage.vintage_year,
                            "is_non_vintage": vintage.is_non_vintage,
                        },
                        "补充适饮期来源和置信度；不要写成绝对结论。",
                    )
                )

        alias_groups = self._alias_groups()
        for (entity_type, alias_key), aliases in alias_groups.items():
            owner_ids = {alias.entity_id for alias in aliases if alias.status in {"approved", "conflict"}}
            if len(owner_ids) > 1 or any(alias.status == "conflict" for alias in aliases):
                findings.append(
                    self._finding(
                        "alias_conflict",
                        "high",
                        entity_type,
                        sorted(owner_ids)[0] if owner_ids else aliases[0].entity_id,
                        {"alias_key": alias_key, "entity_ids": sorted(owner_ids), "alias_ids": [alias.id for alias in aliases]},
                        "人工解决 alias 指向；未解决前不要把 alias 用于稳定匹配。",
                    )
                )
                self._enqueue_missing_queue_once(
                    "alias_conflict",
                    f"Alias 冲突: {alias_key}",
                    "alias_conflict",
                    entity_type,
                    sorted(owner_ids)[0] if owner_ids else aliases[0].entity_id,
                    {"alias_ids": [alias.id for alias in aliases]},
                )

        return findings

    def _producer_search_result(
        self,
        producer: Producer,
        query_key: str,
        aliases: list[RegistryAlias],
    ) -> dict[str, Any] | None:
        if not producer.canonical_key:
            self.apply_producer_fields(producer)
        candidates = [
            self._match_text(query_key, producer.name_original, "canonical_name"),
            self._match_text(query_key, producer.name_cn, "chinese_name"),
            self._match_text(query_key, producer.canonical_key, "canonical_name"),
        ]
        candidates.extend(self._alias_matches(query_key, aliases, producer.aliases))
        return self._search_result(
            entity_id=producer.id,
            entity_type="producer",
            display_name=producer.name_original,
            quality_status=producer.quality_status,
            candidates=candidates,
        )

    def _wine_search_result(
        self,
        wine: Wine,
        query_key: str,
        aliases: list[RegistryAlias],
    ) -> dict[str, Any] | None:
        if not wine.wine_identity_key:
            self.apply_wine_fields(wine, wine.producer)
        producer_name = wine.producer.name_original if wine.producer else None
        candidates = [
            self._match_text(query_key, wine.name_original, "canonical_name"),
            self._match_text(query_key, wine.name_cn, "chinese_name"),
            self._match_text(query_key, wine.wine_identity_key, "canonical_name"),
            self._match_text(query_key, producer_name, "canonical_name"),
        ]
        candidates.extend(self._alias_matches(query_key, aliases, wine.aliases))
        return self._search_result(
            entity_id=wine.id,
            entity_type="wine",
            display_name=self._wine_display_name(wine),
            quality_status=wine.quality_status,
            candidates=candidates,
        )

    def _vintage_search_result(
        self,
        vintage: Vintage,
        query_key: str,
        aliases: list[RegistryAlias],
    ) -> dict[str, Any] | None:
        wine = vintage.wine
        producer = wine.producer if wine else None
        year = "NV" if vintage.is_non_vintage else str(vintage.vintage_year or "")
        display_name = vintage_display_name(vintage)
        candidates = [
            self._match_text(query_key, display_name, "canonical_name"),
            self._match_text(query_key, wine.name_original if wine else None, "canonical_name"),
            self._match_text(query_key, wine.name_cn if wine else None, "chinese_name"),
            self._match_text(query_key, producer.name_original if producer else None, "canonical_name"),
            self._match_text(query_key, producer.name_cn if producer else None, "chinese_name"),
            self._match_year(query_key, year),
        ]
        candidates.extend(self._alias_matches(query_key, aliases, None))
        return self._search_result(
            entity_id=vintage.id,
            entity_type="vintage",
            display_name=display_name,
            quality_status=vintage.quality_status,
            candidates=candidates,
        )

    def _vintage_alias_candidates(
        self,
        vintage: Vintage,
        aliases: dict[tuple[str, str], list[RegistryAlias]],
    ) -> list[RegistryAlias]:
        candidates = list(aliases.get(("vintage", vintage.id), []))
        if vintage.wine:
            candidates.extend(aliases.get(("wine", vintage.wine.id), []))
            if vintage.wine.producer:
                candidates.extend(aliases.get(("producer", vintage.wine.producer.id), []))
        return candidates

    def _wine_alias_candidates(
        self,
        wine: Wine,
        aliases: dict[tuple[str, str], list[RegistryAlias]],
    ) -> list[RegistryAlias]:
        candidates = list(aliases.get(("wine", wine.id), []))
        if wine.producer:
            candidates.extend(aliases.get(("producer", wine.producer.id), []))
        return candidates

    def _search_result(
        self,
        *,
        entity_id: str,
        entity_type: str,
        display_name: str,
        quality_status: str,
        candidates: list[dict[str, Any] | None],
    ) -> dict[str, Any] | None:
        best = self._best_search_candidate(candidates)
        if best is None:
            return None
        score = quality_adjusted_score(best["score"], quality_status)
        if score < 55:
            return None
        return {
            "id": entity_id,
            "entity_type": entity_type,
            "display_name": display_name,
            "matched_text": best["matched_text"],
            "matched_by": best["matched_by"],
            "score": score,
            "quality_status": quality_status,
            "_rank_priority": best["priority"],
        }

    def _match_text(self, query_key: str, value: str | None, matched_by: str) -> dict[str, Any] | None:
        if not value:
            return None
        text_key = normalize_registry_text(value)
        if not text_key:
            return None
        if text_key == query_key:
            return {"matched_text": value, "matched_by": matched_by, "score": 100, "priority": 50}
        if matched_by == "chinese_name" and (query_key in text_key or text_key in query_key):
            return {"matched_text": value, "matched_by": "chinese_name", "score": 92, "priority": 40}
        if query_key in text_key or text_key in query_key:
            return {"matched_text": value, "matched_by": "partial", "score": 82, "priority": 20}
        if len(query_key) < 4:
            return None
        fuzzy_score = round(SequenceMatcher(None, query_key, text_key).ratio() * 100)
        if fuzzy_score >= 70:
            return {"matched_text": value, "matched_by": "fuzzy", "score": min(fuzzy_score, 90), "priority": 30}
        return None

    def _match_year(self, query_key: str, year: str) -> dict[str, Any] | None:
        if not year:
            return None
        year_key = normalize_registry_text(year)
        if year_key == query_key:
            return {"matched_text": year, "matched_by": "canonical_name", "score": 92, "priority": 35}
        return None

    def _alias_matches(
        self,
        query_key: str,
        registry_aliases: list[RegistryAlias],
        embedded_aliases: list[str] | dict[str, Any] | None,
    ) -> list[dict[str, Any] | None]:
        candidates: list[dict[str, Any] | None] = []
        for alias in registry_aliases:
            candidates.append(self._match_alias_text(query_key, alias.alias_text, alias.status))
        for alias_text in self._flatten_aliases(embedded_aliases):
            candidates.append(self._match_alias_text(query_key, alias_text, "observed"))
        return candidates

    def _match_alias_text(self, query_key: str, alias_text: str, status: str) -> dict[str, Any] | None:
        if status == "rejected":
            return None
        alias_key = normalize_registry_text(alias_text)
        if not alias_key:
            return None
        exact_score = {"approved": 96, "candidate": 88, "observed": 86, "conflict": 76}.get(status, 84)
        if alias_key == query_key:
            return {"matched_text": alias_text, "matched_by": "alias", "score": exact_score, "priority": 45}
        if query_key in alias_key or alias_key in query_key:
            partial_score = 84 if status == "approved" else 74
            return {"matched_text": alias_text, "matched_by": "partial", "score": partial_score, "priority": 15}
        if len(query_key) < 4:
            return None
        fuzzy_score = round(SequenceMatcher(None, query_key, alias_key).ratio() * 100)
        if fuzzy_score >= 70:
            return {
                "matched_text": alias_text,
                "matched_by": "fuzzy",
                "score": min(92 if status == "approved" else 82, fuzzy_score),
                "priority": 30,
            }
        return None

    def _best_search_candidate(self, candidates: list[dict[str, Any] | None]) -> dict[str, Any] | None:
        valid_candidates = [candidate for candidate in candidates if candidate is not None]
        if not valid_candidates:
            return None
        return max(valid_candidates, key=lambda item: (item["score"], item["priority"], item["matched_text"]))

    def _top_results(self, results: list[dict[str, Any] | None], limit: int) -> list[dict[str, Any]]:
        valid_results = [result for result in results if result is not None]
        ranked = sorted(valid_results, key=lambda item: (-item["score"], -item["_rank_priority"], item["display_name"]))
        return [{key: value for key, value in result.items() if key != "_rank_priority"} for result in ranked[:limit]]

    def _search_aliases(self) -> dict[tuple[str, str], list[RegistryAlias]]:
        grouped: dict[tuple[str, str], list[RegistryAlias]] = {}
        aliases = self.session.scalars(select(RegistryAlias).where(RegistryAlias.status != "rejected")).all()
        for alias in aliases:
            grouped.setdefault((alias.entity_type, alias.entity_id), []).append(alias)
        return grouped

    def _entity_alias_texts(
        self,
        entity_type: str,
        entity_id: str,
        embedded_aliases: list[str] | dict[str, Any] | None,
    ) -> list[str]:
        aliases = self.session.scalars(
            select(RegistryAlias)
            .where(RegistryAlias.entity_type == entity_type, RegistryAlias.entity_id == entity_id)
            .order_by(RegistryAlias.status.asc(), RegistryAlias.alias_text.asc())
        ).all()
        texts = [alias.alias_text for alias in aliases]
        texts.extend(self._flatten_aliases(embedded_aliases))
        seen: set[str] = set()
        deduped: list[str] = []
        for text in texts:
            key = normalize_registry_text(text)
            if not key or key in seen:
                continue
            seen.add(key)
            deduped.append(text)
        return deduped

    def _flatten_aliases(self, value: list[str] | dict[str, Any] | None) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        if isinstance(value, list | tuple | set):
            aliases: list[str] = []
            for item in value:
                aliases.extend(self._flatten_aliases(item))
            return aliases
        if isinstance(value, dict):
            aliases: list[str] = []
            for item in value.values():
                aliases.extend(self._flatten_aliases(item))
            return aliases
        return []

    def _wine_display_name(self, wine: Wine) -> str:
        if wine.producer:
            return f"{wine.producer.name_original} · {wine.name_original}"
        return wine.name_original

    def _approved_alias_owner(self, entity_type: str, alias_key: str) -> str | None:
        aliases = self.session.scalars(
            select(RegistryAlias).where(
                RegistryAlias.entity_type == entity_type,
                RegistryAlias.alias_key == alias_key,
                RegistryAlias.status == "approved",
            )
        ).all()
        owner_ids = {alias.entity_id for alias in aliases}
        if len(owner_ids) > 1:
            return "conflict"
        return next(iter(owner_ids), None)

    def _alias_conflict(self, entity_type: str, alias_key: str, entity_id: str) -> set[str]:
        aliases = self.session.scalars(
            select(RegistryAlias).where(
                RegistryAlias.entity_type == entity_type,
                RegistryAlias.alias_key == alias_key,
                RegistryAlias.status == "approved",
                RegistryAlias.entity_id != entity_id,
            )
        ).all()
        return {alias.entity_id for alias in aliases}

    def _best_score(self, raw_key: str, candidates: list[tuple[str, str]]) -> tuple[str, str, int] | None:
        if not raw_key or not candidates:
            return None
        scored = [
            (entity_id, candidate_key, round(SequenceMatcher(None, raw_key, candidate_key).ratio() * 100))
            for entity_id, candidate_key in candidates
            if candidate_key
        ]
        if not scored:
            return None
        return max(scored, key=lambda item: item[2])

    def _group_by_key(self, items: list[Any], key_getter) -> dict[str | None, list[Any]]:
        grouped: dict[str | None, list[Any]] = {}
        for item in items:
            grouped.setdefault(key_getter(item), []).append(item)
        return grouped

    def _alias_groups(self) -> dict[tuple[str, str], list[RegistryAlias]]:
        grouped: dict[tuple[str, str], list[RegistryAlias]] = {}
        aliases = self.session.scalars(select(RegistryAlias)).all()
        for alias in aliases:
            grouped.setdefault((alias.entity_type, alias.alias_key), []).append(alias)
        return grouped

    def _finding(
        self,
        finding_type: str,
        severity: str,
        entity_type: str,
        entity_id: str,
        evidence: dict[str, Any],
        suggested_action: str,
    ) -> dict[str, Any]:
        payload = {
            "finding_type": finding_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "evidence": evidence,
        }
        return {
            **payload,
            "severity": severity,
            "evidence_hash": self._evidence_hash(payload),
            "suggested_action": suggested_action,
            "status": "open",
        }

    def _enqueue_missing_queue_once(
        self,
        review_type: str,
        title: str,
        detail: str,
        entity_type: str,
        entity_id: str,
        evidence: dict[str, Any],
    ) -> None:
        existing = self.session.scalar(
            select(RegistryReviewQueue).where(
                RegistryReviewQueue.review_type == review_type,
                RegistryReviewQueue.entity_type == entity_type,
                RegistryReviewQueue.entity_id == entity_id,
                RegistryReviewQueue.title == title,
            )
        )
        if existing is not None:
            return
        self.enqueue_review(
            review_type=review_type,
            title=title,
            detail=detail,
            entity_type=entity_type,
            entity_id=entity_id,
            evidence=evidence,
        )

    def _evidence_hash(self, payload: object) -> str:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()
