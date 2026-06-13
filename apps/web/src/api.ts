import type {
  Bottle,
  Cellar,
  CsvImportConfirmResult,
  CsvImportDraft,
  CsvImportRow,
  DashboardSummary,
  InventoryTransaction,
  LabelDraft,
  LabelDraftConfirmResult,
  LabelImageUpload,
  Location,
  Producer,
  Vintage,
  Wine,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const isFormData = options.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: isFormData
      ? { ...(options.headers ?? {}) }
      : {
          "Content-Type": "application/json",
          ...(options.headers ?? {}),
        },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    let detail: string | undefined;
    try {
      const parsed = JSON.parse(body) as { detail?: unknown; error?: { message?: string } };
      if (typeof parsed.detail === "string") {
        detail = parsed.detail;
      } else if (parsed.detail) {
        detail = JSON.stringify(parsed.detail);
      } else {
        detail = parsed.error?.message;
      }
    } catch {
      detail = undefined;
    }
    throw new Error(detail || body || `${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string }>("/health"),
  dashboard: () => request<DashboardSummary>("/api/dashboard/summary"),
  producers: () => request<Producer[]>("/api/producers"),
  createProducer: (body: Partial<Producer>) =>
    request<Producer>("/api/producers", { method: "POST", body: JSON.stringify(body) }),
  wines: () => request<Wine[]>("/api/wines"),
  createWine: (body: Record<string, unknown>) =>
    request<Wine>("/api/wines", { method: "POST", body: JSON.stringify(body) }),
  vintages: () => request<Vintage[]>("/api/vintages"),
  createVintage: (body: Record<string, unknown>) =>
    request<Vintage>("/api/vintages", { method: "POST", body: JSON.stringify(body) }),
  cellars: () => request<Cellar[]>("/api/cellars"),
  createCellar: (body: Record<string, unknown>) =>
    request<Cellar>("/api/cellars", { method: "POST", body: JSON.stringify(body) }),
  updateCellar: (id: string, body: Record<string, unknown>) =>
    request<Cellar>(`/api/cellars/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  locations: () => request<Location[]>("/api/locations"),
  createLocation: (body: Record<string, unknown>) =>
    request<Location>("/api/locations", { method: "POST", body: JSON.stringify(body) }),
  batchCreateLocations: (cellarId: string, body: Record<string, unknown>) =>
    request<Location[]>(`/api/cellars/${cellarId}/locations/batch`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  cellarGrid: (cellarId: string) => request<Location[]>(`/api/cellars/${cellarId}/grid`),
  bottles: () => request<Bottle[]>("/api/bottles"),
  bottle: (id: string) => request<Bottle>(`/api/bottles/${id}`),
  createBottle: (body: Record<string, unknown>) =>
    request<Bottle>("/api/bottles", { method: "POST", body: JSON.stringify(body) }),
  transactions: () => request<InventoryTransaction[]>("/api/inventory-transactions"),
  createTransaction: (body: Record<string, unknown>) =>
    request<InventoryTransaction>("/api/inventory-transactions", { method: "POST", body: JSON.stringify(body) }),
  createCsvImportDraft: (body: { csv_text: string; filename?: string }) =>
    request<CsvImportDraft>("/api/import/csv/draft", { method: "POST", body: JSON.stringify(body) }),
  confirmCsvImport: (rows: CsvImportRow[]) =>
    request<CsvImportConfirmResult>("/api/import/csv/confirm", {
      method: "POST",
      body: JSON.stringify({ rows }),
    }),
  uploadLabelImage: (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return request<LabelImageUpload>("/api/intake/label-images", { method: "POST", body });
  },
  createLabelDraft: (uploadId: string) =>
    request<LabelDraft>("/api/intake/label-drafts", {
      method: "POST",
      body: JSON.stringify({ upload_id: uploadId }),
    }),
  confirmLabelDraft: (body: Record<string, unknown>) =>
    request<LabelDraftConfirmResult>("/api/intake/label-drafts/confirm", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  bottleCsvUrl: () => `${API_BASE_URL}/api/export/bottles.csv`,
};
