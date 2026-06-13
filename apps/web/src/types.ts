export type Producer = {
  id: string;
  name_original: string;
  name_cn?: string | null;
  country?: string | null;
  region?: string | null;
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
  cellar_name: string;
  location_code: string;
  location_label: string;
  location_key: string;
  raw_status?: string | null;
  raw_cave?: string | null;
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
