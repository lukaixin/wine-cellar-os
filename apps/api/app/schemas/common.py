from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProducerBase(BaseModel):
    name_original: str = Field(min_length=1)
    name_cn: str | None = None
    country: str | None = None
    region: str | None = None
    website: str | None = None
    aliases: list[str] | dict[str, Any] | None = None


class ProducerCreate(ProducerBase):
    pass


class ProducerUpdate(BaseModel):
    name_original: str | None = Field(default=None, min_length=1)
    name_cn: str | None = None
    country: str | None = None
    region: str | None = None
    website: str | None = None
    aliases: list[str] | dict[str, Any] | None = None
    quality_status: str | None = None
    merged_into_id: str | None = None
    reviewed_at: datetime | None = None


class ProducerRead(ProducerBase, OrmModel):
    id: str
    canonical_key: str | None = None
    quality_status: str = "unreviewed"
    merged_into_id: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class WineBase(BaseModel):
    producer_id: str
    name_original: str = Field(min_length=1)
    name_cn: str | None = None
    type: str | None = None
    color: str | None = None
    country: str | None = None
    region: str | None = None
    appellation: str | None = None
    grape_varieties: list[str] | dict[str, Any] | None = None
    classification: str | None = None
    lwin7: str | None = None
    aliases: list[str] | dict[str, Any] | None = None


class WineCreate(WineBase):
    pass


class WineUpdate(BaseModel):
    producer_id: str | None = None
    name_original: str | None = Field(default=None, min_length=1)
    name_cn: str | None = None
    type: str | None = None
    color: str | None = None
    country: str | None = None
    region: str | None = None
    appellation: str | None = None
    grape_varieties: list[str] | dict[str, Any] | None = None
    classification: str | None = None
    lwin7: str | None = None
    aliases: list[str] | dict[str, Any] | None = None
    quality_status: str | None = None
    merged_into_id: str | None = None
    reviewed_at: datetime | None = None


class WineRead(WineBase, OrmModel):
    id: str
    wine_identity_key: str | None = None
    quality_status: str = "unreviewed"
    merged_into_id: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    producer_name: str | None = None


class VintageBase(BaseModel):
    wine_id: str
    vintage_year: int | None = None
    is_non_vintage: bool = False
    lwin11: str | None = None
    critic_score: Decimal | None = None
    critic_source: str | None = None
    default_drink_from: int | None = None
    default_drink_to: int | None = None
    drink_window_confidence: str | None = None
    notes: str | None = None


class VintageCreate(VintageBase):
    pass


class VintageUpdate(BaseModel):
    wine_id: str | None = None
    vintage_year: int | None = None
    is_non_vintage: bool | None = None
    lwin11: str | None = None
    critic_score: Decimal | None = None
    critic_source: str | None = None
    default_drink_from: int | None = None
    default_drink_to: int | None = None
    drink_window_confidence: str | None = None
    notes: str | None = None
    quality_status: str | None = None
    reviewed_at: datetime | None = None


class VintageRead(VintageBase, OrmModel):
    id: str
    quality_status: str = "unreviewed"
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    wine_name: str | None = None
    producer_name: str | None = None


class CellarBase(BaseModel):
    name: str = Field(min_length=1)
    cellar_type: str = Field(default="cabinet", min_length=1)
    rows: int | None = None
    columns: int | None = None
    temperature_target: Decimal | None = None
    humidity_target: Decimal | None = None
    notes: str | None = None


class CellarCreate(CellarBase):
    pass


class CellarUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    cellar_type: str | None = Field(default=None, min_length=1)
    rows: int | None = None
    columns: int | None = None
    temperature_target: Decimal | None = None
    humidity_target: Decimal | None = None
    notes: str | None = None


class CellarRead(CellarBase, OrmModel):
    id: str
    created_at: datetime
    updated_at: datetime


class LocationBase(BaseModel):
    cellar_id: str
    code: str = Field(min_length=1)
    row_index: int | None = None
    column_index: int | None = None
    layer_index: int | None = None
    position_note: str | None = None
    capacity: int = Field(default=1, ge=0)
    location_type: str = "grid"


class LocationCreate(LocationBase):
    pass


class LocationUpdate(BaseModel):
    cellar_id: str | None = None
    code: str | None = Field(default=None, min_length=1)
    row_index: int | None = None
    column_index: int | None = None
    layer_index: int | None = None
    position_note: str | None = None
    capacity: int | None = Field(default=None, ge=0)
    location_type: str | None = None


class LocationRead(LocationBase, OrmModel):
    id: str
    created_at: datetime
    updated_at: datetime
    cellar_name: str | None = None


class CellarLocationBatchCreate(BaseModel):
    rows: int = Field(ge=1, le=200)
    columns: int = Field(ge=1, le=200)
    code_prefix: str = Field(default="A", min_length=1, max_length=24)
    capacity: int = Field(default=1, ge=1)
    location_type: str = "grid"


class BottleCreate(BaseModel):
    vintage_id: str
    current_location_id: str
    bottle_size_ml: int = Field(default=750, gt=0)
    lwin16: str | None = None
    acquisition_date: date | None = None
    purchase_price: Decimal | None = None
    purchase_currency: str = "CNY"
    purchase_source: str | None = None
    purchase_channel: str | None = None
    condition: str | None = None
    personal_rating: int | None = None
    personal_notes: str | None = None
    actor: str | None = "manual"
    note: str | None = None


class BottleUpdate(BaseModel):
    bottle_size_ml: int | None = Field(default=None, gt=0)
    lwin16: str | None = None
    acquisition_date: date | None = None
    purchase_price: Decimal | None = None
    purchase_currency: str | None = None
    purchase_source: str | None = None
    purchase_channel: str | None = None
    condition: str | None = None
    personal_rating: int | None = None
    personal_notes: str | None = None


class BottleRead(OrmModel):
    id: str
    vintage_id: str
    bottle_size_ml: int
    lwin16: str | None
    acquisition_date: date | None
    purchase_price: Decimal | None
    purchase_currency: str
    purchase_source: str | None
    purchase_channel: str | None
    condition: str | None
    current_status: str
    current_location_id: str | None
    personal_rating: int | None
    personal_notes: str | None
    created_at: datetime
    updated_at: datetime
    producer_name: str | None = None
    producer_name_cn: str | None = None
    wine_name: str | None = None
    wine_name_cn: str | None = None
    vintage_year: int | None = None
    is_non_vintage: bool | None = None
    default_drink_from: int | None = None
    default_drink_to: int | None = None
    drink_window_confidence: str | None = None
    drink_window_status: str = "UNKNOWN"
    drink_window_message: str | None = None
    years_until_drink_window: int | None = None
    years_past_drink_window: int | None = None
    wine_type: str | None = None
    country: str | None = None
    cellar_name: str | None = None
    location_code: str | None = None


class CollectionLocationRead(BaseModel):
    id: str | None = None
    cellar_name: str | None = None
    code: str | None = None


class CollectionSearchItem(BaseModel):
    bottle_id: str
    bottle_ids: list[str]
    producer_id: str | None = None
    producer_name: str | None = None
    producer_name_cn: str | None = None
    wine_id: str | None = None
    wine_name: str | None = None
    wine_name_cn: str | None = None
    vintage_id: str
    vintage_year: int | None = None
    is_non_vintage: bool
    bottle_count: int
    location: CollectionLocationRead
    status: str


class CollectionSearchResponse(BaseModel):
    query: str | None = None
    total: int
    limit: int
    offset: int
    items: list[CollectionSearchItem]


class CollectionBottleDetail(BaseModel):
    id: str
    bottle_id: str
    bottle_size_ml: int
    quantity: int = 1
    status: str
    acquisition_date: date | None = None
    vintage_id: str
    vintage_year: int | None = None
    is_non_vintage: bool
    wine_id: str | None = None
    wine_name: str | None = None
    wine_name_cn: str | None = None
    producer_id: str | None = None
    producer_name: str | None = None
    producer_name_cn: str | None = None
    location: CollectionLocationRead
    created_at: datetime
    updated_at: datetime


class CollectionBottleTimelineEvent(BaseModel):
    event_type: str
    event_time: datetime
    quantity_delta: int
    reference_type: Literal["inventory_transaction"]
    reference_id: str
    from_location: CollectionLocationRead
    to_location: CollectionLocationRead
    notes: str | None = None


class InventoryTransactionCreate(BaseModel):
    bottle_id: str
    transaction_type: str
    from_location_id: str | None = None
    to_location_id: str | None = None
    actor: str | None = "manual"
    reason: str | None = None
    note: str | None = None
    occurred_at: datetime | None = None


class InventoryActionQuantity(BaseModel):
    bottle_id: str
    quantity: int = Field(gt=0)
    notes: str | None = None


class ConsumeBottleAction(InventoryActionQuantity):
    pass


class GiftBottleAction(InventoryActionQuantity):
    recipient: str = Field(min_length=1)


class DamageBottleAction(InventoryActionQuantity):
    reason: str = Field(min_length=1)


class MoveBottleAction(BaseModel):
    bottle_id: str
    from_location: str
    to_location: str
    notes: str | None = None


class InventoryTransactionRead(OrmModel):
    id: str
    bottle_id: str
    transaction_type: str
    from_location_id: str | None
    to_location_id: str | None
    occurred_at: datetime
    actor: str | None
    reason: str | None
    note: str | None
    created_at: datetime
    bottle_label: str | None = None
    from_location_code: str | None = None
    to_location_code: str | None = None


DrinkWindowStatusValue = Literal["UNKNOWN", "TOO_EARLY", "ENTERING", "IN_WINDOW", "LATE", "PAST"]


class DashboardBottleInsight(BaseModel):
    bottle_id: str
    bottle_label: str
    producer_name: str | None = None
    wine_name: str | None = None
    vintage_year: int | None = None
    is_non_vintage: bool | None = None
    cellar_name: str | None = None
    location_code: str | None = None
    drink_from: int | None = None
    drink_to: int | None = None
    drink_window_status: DrinkWindowStatusValue
    drink_window_confidence: str | None = None
    reason: str


class DashboardHealthFactor(BaseModel):
    key: str
    label: str
    score: int = Field(ge=0, le=100)
    detail: str


class DashboardHealthScore(BaseModel):
    score: int = Field(ge=0, le=100)
    label: str
    factors: list[DashboardHealthFactor]
    notes: list[str] = Field(default_factory=list)


class DashboardSummary(BaseModel):
    total_bottles: int
    in_stock_bottles: int
    available_bottles: int
    consumed_or_removed_bottles: int
    unavailable_bottles: int
    cellar_count: int
    location_count: int
    recent_transactions: list[InventoryTransactionRead]
    status_counts: dict[str, int]
    drink_window_counts: dict[str, int]
    drink_window_summary: dict[DrinkWindowStatusValue, int]
    upcoming_drink_candidates: list[DashboardBottleInsight]
    past_window_risks: list[DashboardBottleInsight]
    inventory_by_country: dict[str, int]
    inventory_by_type: dict[str, int]
    cellar_occupancy: list[dict[str, int | str]]
    cellar_health_score: DashboardHealthScore


class CsvImportDraftRequest(BaseModel):
    csv_text: str = Field(min_length=1)
    filename: str | None = None


class CsvImportRow(BaseModel):
    producer_name: str
    wine_name: str
    vintage_year: int
    bottle_size_ml: int
    cellar_name: str
    location_code: str
    country: str | None = None
    region: str | None = None
    type: str | None = None
    purchase_price: Decimal | None = None
    purchase_currency: str = "CNY"
    purchase_date: date | None = None
    purchase_source: str | None = None
    drink_from: int | None = None
    drink_to: int | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    cellar_id: str | None = None
    location_id: str | None = None


class CsvImportDraftRow(BaseModel):
    row_number: int
    status: Literal["valid", "invalid"]
    raw: dict[str, str | None]
    normalized: CsvImportRow | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CsvImportDraftResponse(BaseModel):
    filename: str | None = None
    required_fields: list[str]
    optional_fields: list[str]
    total_rows: int
    valid_rows: int
    invalid_rows: int
    errors: list[str] = Field(default_factory=list)
    rows: list[CsvImportDraftRow]


class CsvImportConfirmRequest(BaseModel):
    rows: list[CsvImportRow]


class CsvImportConfirmResponse(BaseModel):
    created_bottles: int
    created_bottle_ids: list[str]
    created_transaction_ids: list[str] = Field(default_factory=list)
    transaction_type: Literal["IN"] = "IN"
    warnings: list[str] = Field(default_factory=list)


class WineListImportNormalizedRow(BaseModel):
    country: str
    region: str
    appellation: str
    producer_name: str
    wine_name: str
    type: str
    vintage_year: int
    quantity: int
    bottle_size_ml: int = 750
    purchase_price: Decimal | None = None
    purchase_currency: str = "CNY"
    purchase_channel: str | None = None
    purchase_source: str
    cellar_name: str
    location_code: str
    location_label: str
    location_key: str
    raw_status: str | None = None
    raw_cave: str | None = None
    producer_match_score: int = Field(default=100, ge=0, le=100)
    wine_match_score: int = Field(default=100, ge=0, le=100)
    vintage_match_score: int = Field(default=100, ge=0, le=100)
    overall_match_score: int = Field(default=100, ge=0, le=100)
    decision: Literal["auto_accepted", "needs_review", "manual_required", "rejected"] = "auto_accepted"


class WineListImportDraftRow(BaseModel):
    id: str | None = None
    row_number: int
    status: Literal["valid", "invalid"]
    raw: dict[str, Any]
    normalized: WineListImportNormalizedRow | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    bottle_count: int = 0


class WineListImportRegistryPreview(BaseModel):
    producers_new: int
    producers_existing: int
    wines_new: int
    wines_existing: int
    vintages_new: int
    vintages_existing: int


class WineListImportDraftResponse(BaseModel):
    batch_id: str
    filename: str
    sheet_name: str = "Stock"
    file_sha256: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    bottle_count: int
    location_counts: dict[str, int]
    registry_preview: WineListImportRegistryPreview
    warnings: list[str] = Field(default_factory=list)
    rows: list[WineListImportDraftRow]


class WineListImportConfirmResponse(BaseModel):
    batch_id: str
    created_bottles: int
    created_bottle_ids: list[str]
    created_transaction_ids: list[str] = Field(default_factory=list)
    location_counts: dict[str, int]
    transaction_type: Literal["IN"] = "IN"
    warnings: list[str] = Field(default_factory=list)


class ImportBatchListItem(BaseModel):
    id: str
    filename: str
    status: str
    created_at: datetime
    confirmed_at: datetime | None = None
    total_rows: int
    success_rows: int
    warning_rows: int
    error_rows: int
    created_bottle_count: int


class ImportBatchListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[ImportBatchListItem]


class ImportBatchDetailRow(BaseModel):
    row_number: int
    raw_values: dict[str, Any]
    parsed_producer: str | None = None
    parsed_wine: str | None = None
    parsed_vintage: int | None = None
    quantity: int | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_bottle_ids: list[str] = Field(default_factory=list)
    ledger_transaction_ids: list[str] = Field(default_factory=list)


class ImportBatchDetailResponse(BaseModel):
    id: str
    filename: str
    sheet_name: str
    file_sha256: str
    status: str
    created_at: datetime
    confirmed_at: datetime | None = None
    total_rows: int
    success_rows: int
    warning_rows: int
    error_rows: int
    created_bottle_count: int
    warnings: list[str] = Field(default_factory=list)
    rows: list[ImportBatchDetailRow]


class RegistryAliasRead(OrmModel):
    id: str
    entity_type: str
    entity_id: str
    alias_text: str
    alias_key: str
    status: str
    source: str | None = None
    rule_version: str
    confidence: str | None = None
    import_mapping_id: str | None = None
    reviewed_at: datetime | None = None
    note: str | None = None
    created_at: datetime
    updated_at: datetime


class ImportMappingRead(OrmModel):
    id: str
    source: str
    import_batch_id: str | None = None
    import_batch_row_id: str | None = None
    source_row_number: int | None = None
    raw_value: dict[str, Any] | str | None = None
    target_entity_type: str
    target_entity_id: str | None = None
    match_score: int
    decision: str
    rule_version: str
    evidence: dict[str, Any] | list[Any] | None = None
    created_at: datetime


class RegistryReviewQueueRead(OrmModel):
    id: str
    review_type: str
    status: str
    source: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    import_mapping_id: str | None = None
    raw_value: dict[str, Any] | str | None = None
    match_score: int | None = None
    title: str
    detail: str | None = None
    evidence: dict[str, Any] | list[Any] | None = None
    created_at: datetime


class RegistryQualityFindingRead(OrmModel):
    id: str
    finding_type: str
    severity: str
    entity_type: str | None = None
    entity_id: str | None = None
    evidence: dict[str, Any] | list[Any]
    evidence_hash: str
    suggested_action: str
    status: str
    created_at: datetime


RegistryEntityType = Literal["producer", "wine", "vintage"]


class RegistrySearchResult(BaseModel):
    id: str
    entity_type: RegistryEntityType
    display_name: str
    matched_text: str
    matched_by: str
    score: int = Field(ge=0, le=100)
    quality_status: str


class RegistrySearchResponse(BaseModel):
    query: str
    producers: list[RegistrySearchResult]
    wines: list[RegistrySearchResult]
    vintages: list[RegistrySearchResult]


class RegistryProducerDetail(BaseModel):
    id: str
    entity_type: Literal["producer"] = "producer"
    canonical_name: str
    name_cn: str | None = None
    aliases: list[str] = Field(default_factory=list)
    country: str | None = None
    region: str | None = None
    wine_count: int
    quality_status: str
    canonical_key: str | None = None


class RegistryWineDetail(BaseModel):
    id: str
    entity_type: Literal["wine"] = "wine"
    canonical_name: str
    name_cn: str | None = None
    producer_id: str
    producer_name: str
    aliases: list[str] = Field(default_factory=list)
    vintage_count: int
    quality_status: str
    wine_identity_key: str | None = None


class RegistryDrinkWindowRead(BaseModel):
    source: str
    source_detail: str | None = None
    drink_from: int | None = None
    drink_to: int | None = None
    peak_from: int | None = None
    peak_to: int | None = None
    confidence: str
    notes: str | None = None


class RegistryVintageDetail(BaseModel):
    id: str
    entity_type: Literal["vintage"] = "vintage"
    producer_id: str
    producer_name: str
    wine_id: str
    wine_name: str
    vintage_year: int | None = None
    is_non_vintage: bool
    bottle_count: int
    default_drink_from: int | None = None
    default_drink_to: int | None = None
    drink_window_confidence: str | None = None
    drink_windows: list[RegistryDrinkWindowRead] = Field(default_factory=list)
    quality_status: str


class RegistryDiscoveryItem(BaseModel):
    id: str
    entity_type: RegistryEntityType
    display_name: str
    created_at: datetime
    quality_status: str


class RegistryQualityRisk(BaseModel):
    id: str
    finding_type: str
    severity: str
    entity_type: str | None = None
    entity_id: str | None = None
    suggested_action: str
    evidence: dict[str, Any] | list[Any]
    created_at: datetime


class RegistryDiscoveryResponse(BaseModel):
    recent_producers: list[RegistryDiscoveryItem]
    recent_wines: list[RegistryDiscoveryItem]
    recent_vintages: list[RegistryDiscoveryItem]
    quality_risks: list[RegistryQualityRisk]


class LabelImageUploadRead(OrmModel):
    id: str
    original_filename: str
    stored_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    file_path: str
    bottle_id: str | None = None
    created_at: datetime


class LabelDraftRequest(BaseModel):
    upload_id: str


class LabelDraftCandidateFields(BaseModel):
    producer_name: str | None = None
    wine_name: str | None = None
    vintage_year: int | None = None
    country: str | None = None
    region: str | None = None
    type: str | None = None
    bottle_size_ml: int | None = None
    notes: str | None = None


class LabelDraftResponse(BaseModel):
    upload: LabelImageUploadRead
    recognizer: str
    confidence: Literal["low", "medium", "high"]
    candidate_fields: LabelDraftCandidateFields
    warnings: list[str] = Field(default_factory=list)


class LabelDraftConfirmRequest(BaseModel):
    upload_id: str
    producer_name: str = Field(min_length=1)
    wine_name: str = Field(min_length=1)
    vintage_year: int = Field(gt=0)
    bottle_size_ml: int = Field(default=750, gt=0)
    location_id: str
    country: str | None = None
    region: str | None = None
    type: str | None = None
    notes: str | None = None


class LabelDraftConfirmResponse(BaseModel):
    bottle_id: str
    upload_id: str
    transaction_type: Literal["IN"] = "IN"
