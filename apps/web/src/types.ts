export type Producer = {
  id: string;
  name_original: string;
  name_cn?: string | null;
  country?: string | null;
  region?: string | null;
  canonical_key?: string | null;
  quality_status?: string | null;
  merged_into_id?: string | null;
  reviewed_at?: string | null;
};

export type Wine = {
  id: string;
  producer_id: string;
  producer_name?: string | null;
  name_original: string;
  name_cn?: string | null;
  type?: string | null;
  country?: string | null;
  region?: string | null;
  wine_identity_key?: string | null;
  quality_status?: string | null;
  merged_into_id?: string | null;
  reviewed_at?: string | null;
};

export type Vintage = {
  id: string;
  wine_id: string;
  wine_name?: string | null;
  producer_name?: string | null;
  vintage_year?: number | null;
  is_non_vintage: boolean;
  default_drink_from?: number | null;
  default_drink_to?: number | null;
  drink_window_confidence?: string | null;
  quality_status?: string | null;
  reviewed_at?: string | null;
};

export type Cellar = {
  id: string;
  name: string;
  cellar_type: string;
  rows?: number | null;
  columns?: number | null;
};

export type Location = {
  id: string;
  cellar_id: string;
  cellar_name?: string | null;
  code: string;
  row_index?: number | null;
  column_index?: number | null;
  capacity: number;
  location_type: string;
};

export type DrinkWindowStatus = "UNKNOWN" | "TOO_EARLY" | "ENTERING" | "IN_WINDOW" | "LATE" | "PAST";

export type Bottle = {
  id: string;
  vintage_id: string;
  bottle_size_ml: number;
  acquisition_date?: string | null;
  purchase_price?: string | null;
  purchase_currency: string;
  purchase_source?: string | null;
  purchase_channel?: string | null;
  ws_price?: string | null;
  condition?: string | null;
  current_status: string;
  current_location_id?: string | null;
  personal_notes?: string | null;
  producer_name?: string | null;
  producer_name_cn?: string | null;
  wine_name?: string | null;
  wine_name_cn?: string | null;
  vintage_year?: number | null;
  is_non_vintage?: boolean | null;
  default_drink_from?: number | null;
  default_drink_to?: number | null;
  drink_window_confidence?: string | null;
  drink_window_status?: DrinkWindowStatus;
  drink_window_message?: string | null;
  years_until_drink_window?: number | null;
  years_past_drink_window?: number | null;
  wine_type?: string | null;
  country?: string | null;
  cellar_name?: string | null;
  location_code?: string | null;
};

export type CollectionLocation = {
  id?: string | null;
  cellar_name?: string | null;
  code?: string | null;
};

export type CollectionSearchItem = {
  bottle_id: string;
  bottle_ids: string[];
  producer_id?: string | null;
  producer_name?: string | null;
  producer_name_cn?: string | null;
  wine_id?: string | null;
  wine_name?: string | null;
  wine_name_cn?: string | null;
  vintage_id: string;
  vintage_year?: number | null;
  is_non_vintage: boolean;
  bottle_count: number;
  location: CollectionLocation;
  status: string;
};

export type CollectionSearchResponse = {
  query?: string | null;
  total: number;
  limit: number;
  offset: number;
  items: CollectionSearchItem[];
};

export type CollectionBottleDetail = {
  id: string;
  bottle_id: string;
  bottle_size_ml: number;
  quantity: number;
  status: string;
  ws_price?: string | null;
  acquisition_date?: string | null;
  vintage_id: string;
  vintage_year?: number | null;
  is_non_vintage: boolean;
  wine_id?: string | null;
  wine_name?: string | null;
  wine_name_cn?: string | null;
  producer_id?: string | null;
  producer_name?: string | null;
  producer_name_cn?: string | null;
  location: CollectionLocation;
  created_at: string;
  updated_at: string;
};

export type CollectionBottleTimelineEvent = {
  event_type: string;
  event_time: string;
  quantity_delta: number;
  reference_type: "inventory_transaction";
  reference_id: string;
  from_location: CollectionLocation;
  to_location: CollectionLocation;
  notes?: string | null;
};

export type InventoryTransaction = {
  id: string;
  bottle_id: string;
  transaction_type: "IN" | "MOVE" | "CONSUME" | "GIFT" | "DAMAGE" | "ADJUST";
  from_location_id?: string | null;
  to_location_id?: string | null;
  occurred_at: string;
  actor?: string | null;
  reason?: string | null;
  note?: string | null;
  bottle_label?: string | null;
  from_location_code?: string | null;
  to_location_code?: string | null;
};

export type ConsumeBottleActionRequest = {
  bottle_id: string;
  quantity: number;
  notes?: string | null;
};

export type GiftBottleActionRequest = ConsumeBottleActionRequest & {
  recipient: string;
};

export type DamageBottleActionRequest = ConsumeBottleActionRequest & {
  reason: string;
};

export type MoveBottleActionRequest = {
  bottle_id: string;
  from_location: string;
  to_location: string;
  notes?: string | null;
};

export type DashboardSummary = {
  total_bottles: number;
  in_stock_bottles: number;
  available_bottles: number;
  consumed_or_removed_bottles: number;
  unavailable_bottles: number;
  cellar_count: number;
  location_count: number;
  recent_transactions: InventoryTransaction[];
  status_counts: Record<string, number>;
  drink_window_counts: Record<string, number>;
  drink_window_summary: Record<DrinkWindowStatus, number>;
  upcoming_drink_candidates: DashboardBottleInsight[];
  past_window_risks: DashboardBottleInsight[];
  inventory_by_country: Record<string, number>;
  inventory_by_type: Record<string, number>;
  cellar_occupancy: Array<{
    cellar_id: string;
    name: string;
    capacity: number;
    occupied: number;
    empty: number;
  }>;
  cellar_health_score: DashboardHealthScore;
};

export type DashboardBottleInsight = {
  bottle_id: string;
  bottle_label: string;
  producer_name?: string | null;
  wine_name?: string | null;
  vintage_year?: number | null;
  is_non_vintage?: boolean | null;
  cellar_name?: string | null;
  location_code?: string | null;
  drink_from?: number | null;
  drink_to?: number | null;
  drink_window_status: DrinkWindowStatus;
  drink_window_confidence?: string | null;
  reason: string;
};

export type DashboardHealthFactor = {
  key: string;
  label: string;
  score: number;
  detail: string;
};

export type DashboardHealthScore = {
  score: number;
  label: string;
  factors: DashboardHealthFactor[];
  notes: string[];
};

export type CsvImportRow = {
  producer_name: string;
  wine_name: string;
  vintage_year: number;
  bottle_size_ml: number;
  cellar_name: string;
  location_code: string;
  country?: string | null;
  region?: string | null;
  type?: string | null;
  purchase_price?: string | null;
  purchase_currency: string;
  purchase_date?: string | null;
  purchase_source?: string | null;
  drink_from?: number | null;
  drink_to?: number | null;
  notes?: string | null;
  tags: string[];
  cellar_id?: string | null;
  location_id?: string | null;
};

export type CsvImportDraftRow = {
  row_number: number;
  status: "valid" | "invalid";
  raw: Record<string, string | null>;
  normalized?: CsvImportRow | null;
  errors: string[];
  warnings: string[];
};

export type CsvImportDraft = {
  filename?: string | null;
  required_fields: string[];
  optional_fields: string[];
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  errors: string[];
  rows: CsvImportDraftRow[];
};

export type CsvImportConfirmResult = {
  created_bottles: number;
  created_bottle_ids: string[];
  created_transaction_ids: string[];
  transaction_type: "IN";
  warnings: string[];
};

export type WineListImportNormalizedRow = {
  country: string;
  region: string;
  appellation: string;
  producer_name: string;
  wine_name: string;
  type: string;
  vintage_year: number;
  quantity: number;
  bottle_size_ml: number;
  purchase_price?: string | null;
  purchase_currency: string;
  purchase_channel?: string | null;
  purchase_source: string;
  ws_price?: string | null;
  cellar_name: string;
  location_code: string;
  location_label: string;
  location_key: string;
  raw_status?: string | null;
  raw_cave?: string | null;
  producer_match_score: number;
  wine_match_score: number;
  vintage_match_score: number;
  overall_match_score: number;
  decision: "auto_accepted" | "needs_review" | "manual_required" | "rejected";
};

export type WineListImportDraftRow = {
  id?: string | null;
  row_number: number;
  status: "valid" | "invalid";
  raw: Record<string, unknown>;
  normalized?: WineListImportNormalizedRow | null;
  errors: string[];
  warnings: string[];
  bottle_count: number;
};

export type WineListImportRegistryPreview = {
  producers_new: number;
  producers_existing: number;
  wines_new: number;
  wines_existing: number;
  vintages_new: number;
  vintages_existing: number;
};

export type WineListImportDraft = {
  batch_id: string;
  filename: string;
  sheet_name: string;
  file_sha256: string;
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  bottle_count: number;
  location_counts: Record<string, number>;
  registry_preview: WineListImportRegistryPreview;
  warnings: string[];
  rows: WineListImportDraftRow[];
};

export type WineListImportConfirmResult = {
  batch_id: string;
  created_bottles: number;
  created_bottle_ids: string[];
  created_transaction_ids: string[];
  location_counts: Record<string, number>;
  transaction_type: "IN";
  warnings: string[];
};

export type ImportBatchListItem = {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  confirmed_at?: string | null;
  total_rows: number;
  success_rows: number;
  warning_rows: number;
  error_rows: number;
  created_bottle_count: number;
};

export type ImportBatchListResponse = {
  total: number;
  limit: number;
  offset: number;
  items: ImportBatchListItem[];
};

export type ImportBatchDetailRow = {
  row_number: number;
  raw_values: Record<string, unknown>;
  parsed_producer?: string | null;
  parsed_wine?: string | null;
  parsed_vintage?: number | null;
  quantity?: number | null;
  warnings: string[];
  errors: string[];
  created_bottle_ids: string[];
  ledger_transaction_ids: string[];
};

export type ImportBatchDetail = {
  id: string;
  filename: string;
  sheet_name: string;
  file_sha256: string;
  status: string;
  created_at: string;
  confirmed_at?: string | null;
  total_rows: number;
  success_rows: number;
  warning_rows: number;
  error_rows: number;
  created_bottle_count: number;
  warnings: string[];
  rows: ImportBatchDetailRow[];
};

export type LabelImageUpload = {
  id: string;
  original_filename: string;
  stored_filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  file_path: string;
  bottle_id?: string | null;
  created_at: string;
};

export type LabelDraftCandidateFields = {
  producer_name?: string | null;
  wine_name?: string | null;
  vintage_year?: number | null;
  country?: string | null;
  region?: string | null;
  type?: string | null;
  bottle_size_ml?: number | null;
  notes?: string | null;
};

export type LabelDraft = {
  upload: LabelImageUpload;
  recognizer: string;
  confidence: "low" | "medium" | "high";
  candidate_fields: LabelDraftCandidateFields;
  warnings: string[];
};

export type LabelDraftConfirmResult = {
  bottle_id: string;
  upload_id: string;
  transaction_type: "IN";
};

export type RegistryAlias = {
  id: string;
  entity_type: "producer" | "wine" | "vintage";
  entity_id: string;
  alias_text: string;
  alias_key: string;
  status: "observed" | "candidate" | "approved" | "rejected" | "conflict";
  source?: string | null;
  rule_version: string;
  confidence?: string | null;
  import_mapping_id?: string | null;
  reviewed_at?: string | null;
  note?: string | null;
  created_at: string;
  updated_at: string;
};

export type ImportMapping = {
  id: string;
  source: string;
  import_batch_id?: string | null;
  import_batch_row_id?: string | null;
  source_row_number?: number | null;
  raw_value?: Record<string, unknown> | string | null;
  target_entity_type: "producer" | "wine" | "vintage";
  target_entity_id?: string | null;
  match_score: number;
  decision: "auto_accepted" | "needs_review" | "manual_required" | "rejected";
  rule_version: string;
  evidence?: Record<string, unknown> | unknown[] | null;
  created_at: string;
};

export type RegistryReviewQueueItem = {
  id: string;
  review_type: "match_range" | "alias_conflict" | "suspected_duplicate" | "missing_field";
  status: "open" | "closed";
  source?: string | null;
  entity_type?: string | null;
  entity_id?: string | null;
  import_mapping_id?: string | null;
  raw_value?: Record<string, unknown> | string | null;
  match_score?: number | null;
  title: string;
  detail?: string | null;
  evidence?: Record<string, unknown> | unknown[] | null;
  created_at: string;
};

export type RegistryQualityFinding = {
  id: string;
  finding_type:
    | "duplicate_producer"
    | "duplicate_wine"
    | "alias_conflict"
    | "missing_vintage"
    | "missing_drink_window"
    | "missing_region"
    | "missing_country";
  severity: "low" | "medium" | "high";
  entity_type?: string | null;
  entity_id?: string | null;
  evidence: Record<string, unknown> | unknown[];
  evidence_hash: string;
  suggested_action: string;
  status: "open" | "closed";
  created_at: string;
};

export type RegistryQualityData = {
  aliases: RegistryAlias[];
  importMappings: ImportMapping[];
  reviewQueue: RegistryReviewQueueItem[];
  findings: RegistryQualityFinding[];
};

export type RegistryEntityType = "producer" | "wine" | "vintage";

export type RegistrySearchResult = {
  id: string;
  entity_type: RegistryEntityType;
  display_name: string;
  matched_text: string;
  matched_by: "canonical_name" | "alias" | "fuzzy" | "chinese_name" | "partial" | string;
  score: number;
  quality_status: string;
};

export type RegistrySearchResponse = {
  query: string;
  producers: RegistrySearchResult[];
  wines: RegistrySearchResult[];
  vintages: RegistrySearchResult[];
};

export type RegistryProducerDetail = {
  id: string;
  entity_type: "producer";
  canonical_name: string;
  name_cn?: string | null;
  aliases: string[];
  country?: string | null;
  region?: string | null;
  wine_count: number;
  quality_status: string;
  canonical_key?: string | null;
};

export type RegistryWineDetail = {
  id: string;
  entity_type: "wine";
  canonical_name: string;
  name_cn?: string | null;
  producer_id: string;
  producer_name: string;
  aliases: string[];
  vintage_count: number;
  quality_status: string;
  wine_identity_key?: string | null;
};

export type RegistryDrinkWindow = {
  source: string;
  source_detail?: string | null;
  drink_from?: number | null;
  drink_to?: number | null;
  peak_from?: number | null;
  peak_to?: number | null;
  confidence: string;
  notes?: string | null;
};

export type RegistryVintageDetail = {
  id: string;
  entity_type: "vintage";
  producer_id: string;
  producer_name: string;
  wine_id: string;
  wine_name: string;
  vintage_year?: number | null;
  is_non_vintage: boolean;
  bottle_count: number;
  default_drink_from?: number | null;
  default_drink_to?: number | null;
  drink_window_confidence?: string | null;
  drink_windows: RegistryDrinkWindow[];
  quality_status: string;
};

export type RegistryDetail = RegistryProducerDetail | RegistryWineDetail | RegistryVintageDetail;

export type RegistryDiscoveryItem = {
  id: string;
  entity_type: RegistryEntityType;
  display_name: string;
  created_at: string;
  quality_status: string;
};

export type RegistryQualityRisk = {
  id: string;
  finding_type: string;
  severity: "low" | "medium" | "high";
  entity_type?: RegistryEntityType | string | null;
  entity_id?: string | null;
  suggested_action: string;
  evidence: Record<string, unknown> | unknown[];
  created_at: string;
};

export type RegistryDiscovery = {
  recent_producers: RegistryDiscoveryItem[];
  recent_wines: RegistryDiscoveryItem[];
  recent_vintages: RegistryDiscoveryItem[];
  quality_risks: RegistryQualityRisk[];
};

export type AnalyticsDistributionItem = {
  label: string;
  count: number;
};

export type AnalyticsInventorySummary = {
  total_bottles: number;
  total_wines: number;
  total_producers: number;
  total_vintages: number;
  total_ws_value?: string | null;
  ws_priced_bottles: number;
  country_distribution: AnalyticsDistributionItem[];
  region_distribution: AnalyticsDistributionItem[];
  vintage_distribution: AnalyticsDistributionItem[];
  status_distribution: AnalyticsDistributionItem[];
};

export type AnalyticsConsumptionPeriod = {
  key: "last_30_days" | "last_90_days" | "all_time";
  label: string;
  consumed_bottles: number;
  gifted_bottles: number;
  damaged_bottles: number;
};

export type AnalyticsMonthlyConsumption = {
  month: string;
  consumed_bottles: number;
  gifted_bottles: number;
  damaged_bottles: number;
};

export type AnalyticsActivityItem = {
  event_type: "IMPORT" | "CONSUME" | "GIFT" | "MOVE" | "DAMAGE";
  transaction_id: string;
  bottle_id: string;
  bottle_label?: string | null;
  occurred_at: string;
  actor?: string | null;
  reason?: string | null;
  note?: string | null;
  from_location: CollectionLocation;
  to_location: CollectionLocation;
};

export type AnalyticsSummary = {
  inventory: AnalyticsInventorySummary;
  consumption: {
    periods: AnalyticsConsumptionPeriod[];
    monthly_trend: AnalyticsMonthlyConsumption[];
  };
  activity: AnalyticsActivityItem[];
};

export type AppData = {
  dashboard?: DashboardSummary;
  producers: Producer[];
  wines: Wine[];
  vintages: Vintage[];
  cellars: Cellar[];
  locations: Location[];
  bottles: Bottle[];
  transactions: InventoryTransaction[];
};
