import { FormEvent, useState } from "react";
import { api } from "../api";
import type { CsvImportDraft } from "../types";
import { DataTable } from "../components/ui/DataTable";
import { Metric } from "../components/ui/Summary";

export function CsvImportPage({
  afterMutation,
  openBottle,
}: {
  afterMutation: (message: string) => Promise<void>;
  openBottle: (id: string) => void;
}) {
  const [filename, setFilename] = useState("");
  const [csvText, setCsvText] = useState("");
  const [draft, setDraft] = useState<CsvImportDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function handleFileChange(event: FormEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    setDraft(null);
    setError(null);
    setWarning(null);
    if (!file) return;
    setFilename(file.name);
    setCsvText(await file.text());
  }

  async function parseDraft(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setWarning(null);
    setParsing(true);
    try {
      const result = await api.createCsvImportDraft({ csv_text: csvText, filename: filename || undefined });
      setDraft(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV 解析失败");
    } finally {
      setParsing(false);
    }
  }

  async function confirmImport() {
    if (!draft) return;
    const rowsToConfirm = draft.rows.flatMap((row) => (row.status === "valid" && row.normalized ? [row.normalized] : []));
    if (!rowsToConfirm.length || draft.invalid_rows > 0) {
      setError("仍有无效行，不能确认导入。");
      return;
    }
    setError(null);
    setWarning(null);
    setConfirming(true);
    try {
      const result = await api.confirmCsvImport(rowsToConfirm);
      if (result.warnings.length) setWarning(result.warnings.join("; "));
      setDraft(null);
      setCsvText("");
      setFilename("");
      await afterMutation(`CSV 已导入 ${result.created_bottles} 瓶`);
      if (result.created_bottle_ids[0]) openBottle(result.created_bottle_ids[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "CSV 确认导入失败");
    } finally {
      setConfirming(false);
    }
  }

  const canConfirm = Boolean(draft && draft.valid_rows > 0 && draft.invalid_rows === 0);

  return (
    <section className="stack">
      <form className="panel import-panel" onSubmit={parseDraft}>
        <h2>CSV 导入草稿</h2>
        <div className="fields">
          <label>
            <span>CSV 文件</span>
            <input accept=".csv,text/csv" type="file" onChange={handleFileChange} />
          </label>
          <label>
            <span>CSV 内容</span>
            <textarea value={csvText} onChange={(event) => setCsvText(event.target.value)} />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={parsing || !csvText.trim()}>
              {parsing ? "解析中" : "解析草稿"}
            </button>
            <button className="secondary" type="button" disabled={!canConfirm || confirming} onClick={confirmImport}>
              {confirming ? "导入中" : "确认导入"}
            </button>
          </div>
        </div>
      </form>
      {error && <div className="banner error">{error}</div>}
      {warning && <div className="banner warning">{warning}</div>}
      {draft && (
        <section className="panel stack">
          <div className="metric-grid">
            <Metric label="总行数" value={draft.total_rows} />
            <Metric label="有效行" value={draft.valid_rows} />
            <Metric label="错误行" value={draft.invalid_rows} />
            <Metric label="确认状态" value={canConfirm ? "可确认" : "需修正"} />
          </div>
          {draft.errors.length > 0 && <div className="banner error">{draft.errors.join("; ")}</div>}
          <DataTable
            headers={["行", "状态", "酒庄", "酒款", "年份", "位置", "错误 / 提醒"]}
            empty="暂无 CSV 草稿。"
            rows={draft.rows.map((row) => ({
              key: String(row.row_number),
              cells: [
                row.row_number,
                row.status === "valid" ? "有效" : "无效",
                row.normalized?.producer_name ?? row.raw.producer_name ?? "-",
                row.normalized?.wine_name ?? row.raw.wine_name ?? "-",
                row.normalized?.vintage_year ?? row.raw.vintage_year ?? "-",
                row.normalized
                  ? `${row.normalized.cellar_name} / ${row.normalized.location_code}`
                  : [row.raw.cellar_name, row.raw.location_code].filter(Boolean).join(" / ") || "-",
                [...row.errors, ...row.warnings].join("; ") || "-",
              ],
            }))}
          />
        </section>
      )}
    </section>
  );
}
