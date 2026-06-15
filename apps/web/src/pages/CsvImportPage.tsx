import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { CsvImportDraft, ImportBatchDetail, ImportBatchListItem, WineListImportDraft } from "../types";
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
  const [wineListFile, setWineListFile] = useState<File | null>(null);
  const [wineListDraft, setWineListDraft] = useState<WineListImportDraft | null>(null);
  const [importBatches, setImportBatches] = useState<ImportBatchListItem[]>([]);
  const [batchTotal, setBatchTotal] = useState(0);
  const [selectedBatch, setSelectedBatch] = useState<ImportBatchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [wineListParsing, setWineListParsing] = useState(false);
  const [wineListConfirming, setWineListConfirming] = useState(false);
  const [batchesLoading, setBatchesLoading] = useState(false);
  const [batchDetailLoading, setBatchDetailLoading] = useState(false);
  const [compensating, setCompensating] = useState(false);
  const [compensationReason, setCompensationReason] = useState("");

  useEffect(() => {
    void refreshImportBatches();
  }, []);

  async function refreshImportBatches() {
    setBatchesLoading(true);
    try {
      const result = await api.importBatches(50, 0);
      setImportBatches(result.items);
      setBatchTotal(result.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入批次加载失败");
    } finally {
      setBatchesLoading(false);
    }
  }

  async function openBatchDetail(batchId: string) {
    setBatchDetailLoading(true);
    setError(null);
    try {
      const result = await api.importBatch(batchId);
      setSelectedBatch(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入批次详情加载失败");
    } finally {
      setBatchDetailLoading(false);
    }
  }

  async function handleFileChange(event: FormEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0];
    setDraft(null);
    setError(null);
    setWarning(null);
    if (!file) return;
    setFilename(file.name);
    setCsvText(await file.text());
  }

  function handleWineListFileChange(event: FormEvent<HTMLInputElement>) {
    const file = event.currentTarget.files?.[0] ?? null;
    setWineListDraft(null);
    setWineListFile(file);
    setError(null);
    setWarning(null);
  }

  async function parseWineListDraft(event: FormEvent) {
    event.preventDefault();
    if (!wineListFile) return;
    setError(null);
    setWarning(null);
    setWineListParsing(true);
    try {
      const result = await api.createWineListImportDraft(wineListFile);
      setWineListDraft(result);
      await refreshImportBatches();
      await openBatchDetail(result.batch_id);
      if (result.warnings.length) setWarning(result.warnings.join("; "));
    } catch (err) {
      setError(err instanceof Error ? err.message : "WineList 解析失败");
    } finally {
      setWineListParsing(false);
    }
  }

  async function confirmWineListImport() {
    if (!wineListDraft) return;
    if (wineListDraft.invalid_rows > 0 || wineListDraft.valid_rows === 0) {
      setError("WineList 仍有无效行，不能确认导入。");
      return;
    }
    setError(null);
    setWarning(null);
    setWineListConfirming(true);
    try {
      const result = await api.confirmWineListImport(wineListDraft.batch_id);
      if (result.warnings.length) setWarning(result.warnings.join("; "));
      setWineListDraft(null);
      setWineListFile(null);
      await afterMutation(`WineList 已导入 ${result.created_bottles} 瓶`);
      await refreshImportBatches();
      await openBatchDetail(result.batch_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "WineList 确认导入失败");
    } finally {
      setWineListConfirming(false);
    }
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

  async function compensateSelectedBatch() {
    if (!selectedBatch) return;
    if (!selectedBatch.can_compensate) {
      setError("当前批次不能补偿。");
      return;
    }
    if (!compensationReason.trim()) {
      setError("请填写补偿原因。");
      return;
    }
    if (!window.confirm(`Compensate ${selectedBatch.created_bottle_count} bottles from ${selectedBatch.filename}?`)) {
      return;
    }
    setError(null);
    setWarning(null);
    setCompensating(true);
    try {
      const result = await api.compensateImportBatch(selectedBatch.id, {
        reason: compensationReason,
        confirm_bottle_count: selectedBatch.created_bottle_count,
      });
      setWarning(`已补偿 ${result.compensated_bottles} 瓶，生成 ${result.compensation_transaction_ids.length} 条 ADJUST ledger。`);
      setCompensationReason("");
      await afterMutation(`Import batch 已补偿 ${result.compensated_bottles} 瓶`);
      await refreshImportBatches();
      await openBatchDetail(selectedBatch.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "导入补偿失败");
    } finally {
      setCompensating(false);
    }
  }

  const canConfirm = Boolean(draft && draft.valid_rows > 0 && draft.invalid_rows === 0);
  const canConfirmWineList = Boolean(wineListDraft && wineListDraft.valid_rows > 0 && wineListDraft.invalid_rows === 0);
  const formatDate = (value?: string | null) => (value ? new Date(value).toLocaleString("zh-CN") : "-");
  const joinList = (items: string[]) => items.join(", ") || "-";
  const idList = (items: string[]) => (
    <span className="id-list">{items.length ? items.join(", ") : "-"}</span>
  );

  return (
    <section className="stack">
      <form className="panel import-panel" onSubmit={parseWineListDraft}>
        <h2>WineList Excel 正式库存导入</h2>
        <div className="fields">
          <label>
            <span>WineList.xlsx 文件</span>
            <input
              accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              type="file"
              onChange={handleWineListFileChange}
            />
          </label>
          <div className="form-actions">
            <button type="submit" disabled={wineListParsing || !wineListFile}>
              {wineListParsing ? "解析中" : "解析 WineList"}
            </button>
            <button
              className="secondary"
              type="button"
              disabled={!canConfirmWineList || wineListConfirming}
              onClick={confirmWineListImport}
            >
              {wineListConfirming ? "导入中" : "确认导入 WineList"}
            </button>
          </div>
        </div>
      </form>

      {error && <div className="banner error">{error}</div>}
      {warning && <div className="banner warning">{warning}</div>}

      {wineListDraft && (
        <section className="panel stack">
          <h2>WineList dry-run 结果</h2>
          <div className="metric-grid">
            <Metric label="库存行" value={wineListDraft.total_rows} />
            <Metric label="有效行" value={wineListDraft.valid_rows} />
            <Metric label="无效行" value={wineListDraft.invalid_rows} />
            <Metric label="展开瓶数" value={wineListDraft.bottle_count} />
            <Metric label="确认状态" value={canConfirmWineList ? "可确认" : "需修正"} />
          </div>
          <div className="metric-grid">
            <Metric label="新 Producer" value={wineListDraft.registry_preview.producers_new} />
            <Metric label="复用 Producer" value={wineListDraft.registry_preview.producers_existing} />
            <Metric label="新 Wine" value={wineListDraft.registry_preview.wines_new} />
            <Metric label="新 Vintage" value={wineListDraft.registry_preview.vintages_new} />
          </div>
          <DataTable
            headers={["位置", "瓶数"]}
            empty="暂无位置汇总。"
            rows={Object.entries(wineListDraft.location_counts).map(([label, count]) => ({
              key: label,
              cells: [label, count],
            }))}
          />
          <DataTable
            headers={["行", "状态", "Producer", "Wine", "年份", "数量", "匹配分", "Decision", "位置", "成本", "错误 / 提醒"]}
            empty="暂无 WineList 草稿。"
            rows={wineListDraft.rows.map((row) => ({
              key: String(row.row_number),
              cells: [
                row.row_number,
                row.status === "valid" ? "有效" : "无效",
                row.normalized?.producer_name ?? String(row.raw.Producer ?? "-"),
                row.normalized?.wine_name ?? String(row.raw.Wine ?? "-"),
                row.normalized?.vintage_year ?? String(row.raw.Vintage ?? "-"),
                row.normalized?.quantity ?? String(row.raw.Quantity ?? "-"),
                row.normalized
                  ? `${row.normalized.producer_match_score}/${row.normalized.wine_match_score}/${row.normalized.vintage_match_score} (${row.normalized.overall_match_score})`
                  : "-",
                row.normalized?.decision ?? "-",
                row.normalized?.location_label ?? "-",
                row.normalized?.purchase_price ?? "-",
                [...row.errors, ...row.warnings].join("; ") || "-",
              ],
            }))}
          />
        </section>
      )}

      <section className="panel stack">
        <div className="section-heading">
          <div>
            <h2>Import Batch History</h2>
            <span className="subtle">共 {batchTotal} 个批次</span>
          </div>
          <button className="secondary" type="button" onClick={refreshImportBatches} disabled={batchesLoading}>
            {batchesLoading ? "刷新中" : "刷新历史"}
          </button>
        </div>
        <DataTable
          headers={["文件", "状态", "创建时间", "确认时间", "补偿时间", "行数", "成功行", "Warning 行", "Error 行", "创建瓶数", "补偿瓶数", "操作"]}
          empty="暂无导入批次。"
          rows={importBatches.map((batch) => ({
            key: batch.id,
            cells: [
              batch.filename,
              batch.compensated_at ? "compensated" : batch.status,
              formatDate(batch.created_at),
              formatDate(batch.confirmed_at),
              formatDate(batch.compensated_at),
              batch.total_rows,
              batch.success_rows,
              batch.warning_rows,
              batch.error_rows,
              batch.created_bottle_count,
              batch.compensated_bottle_count,
              <button
                className="secondary compact-button"
                type="button"
                onClick={() => void openBatchDetail(batch.id)}
                disabled={batchDetailLoading}
              >
                查看
              </button>,
            ],
          }))}
        />
      </section>

      {selectedBatch && (
        <section className="panel stack">
          <div className="section-heading">
            <div>
              <h2>Import Batch Detail</h2>
              <span className="subtle">{selectedBatch.filename} / {selectedBatch.sheet_name}</span>
            </div>
            <span className="status-pill">{selectedBatch.status}</span>
          </div>
          <div className="metric-grid">
            <Metric label="总行数" value={selectedBatch.total_rows} />
            <Metric label="成功行" value={selectedBatch.success_rows} />
            <Metric label="Warning 行" value={selectedBatch.warning_rows} />
            <Metric label="Error 行" value={selectedBatch.error_rows} />
            <Metric label="创建瓶数" value={selectedBatch.created_bottle_count} />
            <Metric label="补偿瓶数" value={selectedBatch.compensated_bottle_count} />
          </div>
          <div className="info-grid">
            <div className="info-item">
              <span>Batch ID</span>
              <strong>{selectedBatch.id}</strong>
            </div>
            <div className="info-item">
              <span>文件 hash</span>
              <strong>{selectedBatch.file_sha256}</strong>
            </div>
            <div className="info-item">
              <span>创建时间</span>
              <strong>{formatDate(selectedBatch.created_at)}</strong>
            </div>
            <div className="info-item">
              <span>确认时间</span>
              <strong>{formatDate(selectedBatch.confirmed_at)}</strong>
            </div>
            <div className="info-item">
              <span>补偿时间</span>
              <strong>{formatDate(selectedBatch.compensated_at)}</strong>
            </div>
            <div className="info-item">
              <span>补偿 Ledger</span>
              <strong>{selectedBatch.compensation_transaction_ids.length}</strong>
            </div>
          </div>
          {selectedBatch.warnings.length > 0 && <div className="banner warning">{selectedBatch.warnings.join("; ")}</div>}
          {selectedBatch.compensation_reason && <div className="banner success">补偿原因：{selectedBatch.compensation_reason}</div>}
          <section className="sub-panel stack">
            <div className="section-heading">
              <div>
                <h3>Import Compensation</h3>
                <span className="subtle">使用 ADJUST ledger 补偿误导入影响，不删除历史。</span>
              </div>
              <span className="status-pill">{selectedBatch.can_compensate ? "可补偿" : "不可补偿"}</span>
            </div>
            <div className="metric-grid">
              <Metric label="影响瓶数" value={selectedBatch.created_bottle_count} />
              <Metric label="原始 IN Ledger" value={selectedBatch.rows.reduce((sum, row) => sum + row.ledger_transaction_ids.length, 0)} />
              <Metric label="补偿 Ledger" value={selectedBatch.compensation_transaction_ids.length} />
            </div>
            {selectedBatch.compensation_blockers.length > 0 && (
              <div className="banner warning">{selectedBatch.compensation_blockers.join("; ")}</div>
            )}
            <label>
              <span>补偿原因</span>
              <textarea
                value={compensationReason}
                disabled={!selectedBatch.can_compensate || compensating}
                onChange={(event) => setCompensationReason(event.target.value)}
              />
            </label>
            <div className="form-actions">
              <button
                type="button"
                disabled={!selectedBatch.can_compensate || compensating || !compensationReason.trim()}
                onClick={compensateSelectedBatch}
              >
                {compensating ? "补偿中" : "Compensate"}
              </button>
            </div>
          </section>
          <DataTable
            className="review-table"
            headers={["行", "解析结果", "数量", "Raw values", "Warnings", "Errors", "Bottle IDs", "Transaction IDs"]}
            empty="暂无批次行。"
            rows={selectedBatch.rows.map((row) => ({
              key: String(row.row_number),
              cells: [
                row.row_number,
                [row.parsed_producer, row.parsed_wine, row.parsed_vintage].filter(Boolean).join(" / ") || "-",
                row.quantity ?? "-",
                <code className="raw-json">{JSON.stringify(row.raw_values)}</code>,
                joinList(row.warnings),
                joinList(row.errors),
                idList(row.created_bottle_ids),
                idList(row.ledger_transaction_ids),
              ],
            }))}
          />
        </section>
      )}

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
