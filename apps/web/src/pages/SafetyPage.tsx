import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { DataTable } from "../components/ui/DataTable";
import { Metric } from "../components/ui/Summary";
import type { BackupItem } from "../types";

export function SafetyPage({ afterMutation }: { afterMutation: (message: string) => Promise<void> }) {
  const [databasePath, setDatabasePath] = useState("");
  const [backupDir, setBackupDir] = useState("");
  const [backups, setBackups] = useState<BackupItem[]>([]);
  const [selectedBackup, setSelectedBackup] = useState<BackupItem | null>(null);
  const [restoreReason, setRestoreReason] = useState("");
  const [confirmationText, setConfirmationText] = useState("");
  const [confirmedImpact, setConfirmedImpact] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    void refreshBackups();
  }, []);

  async function refreshBackups() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.backups();
      setDatabasePath(result.database_path);
      setBackupDir(result.backup_dir);
      setBackups(result.backups);
    } catch (err) {
      setError(err instanceof Error ? err.message : "备份列表加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function createBackup() {
    setCreating(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api.createBackup();
      setNotice(`Backup created: ${result.filename}`);
      await refreshBackups();
    } catch (err) {
      setError(err instanceof Error ? err.message : "备份创建失败");
    } finally {
      setCreating(false);
    }
  }

  async function restoreBackup(event: FormEvent) {
    event.preventDefault();
    if (!selectedBackup) return;
    if (!confirmedImpact) {
      setError("恢复前必须确认会替换当前数据库文件。");
      return;
    }
    if (!window.confirm(`Restore ${selectedBackup.filename}? 当前数据库会先创建 pre-restore backup。`)) {
      return;
    }
    setRestoring(true);
    setError(null);
    setNotice(null);
    try {
      const result = await api.restoreBackup({
        filename: selectedBackup.filename,
        confirmation_text: confirmationText,
        reason: restoreReason,
      });
      setNotice(`Restored from ${selectedBackup.filename}; event ${result.event_id}`);
      setRestoreReason("");
      setConfirmationText("");
      setConfirmedImpact(false);
      setSelectedBackup(null);
      await refreshBackups();
      await afterMutation("数据库恢复已完成，请刷新页面数据。");
    } catch (err) {
      setError(err instanceof Error ? err.message : "数据库恢复失败");
    } finally {
      setRestoring(false);
    }
  }

  const canRestore = Boolean(selectedBackup && restoreReason.trim() && confirmationText === "RESTORE" && confirmedImpact);
  const formatDate = (value: string) => new Date(value).toLocaleString("zh-CN");
  const formatSize = (value: number) => `${(value / 1024).toFixed(1)} KB`;

  return (
    <section className="stack">
      {error && <div className="banner error">{error}</div>}
      {notice && <div className="banner success">{notice}</div>}

      <section className="panel stack">
        <div className="section-heading">
          <div>
            <h2>Backup & Restore</h2>
            <span className="subtle">本地 SQLite 安全操作</span>
          </div>
          <button className="secondary" type="button" onClick={refreshBackups} disabled={loading}>
            {loading ? "刷新中" : "刷新"}
          </button>
        </div>
        <div className="metric-grid">
          <Metric label="Backups" value={backups.length} />
          <Metric label="Database" value={databasePath ? "已定位" : "未加载"} />
          <Metric label="Backup Dir" value={backupDir ? "已定位" : "未加载"} />
        </div>
        <div className="info-grid">
          <div className="info-item">
            <span>Database Path</span>
            <strong>{databasePath || "-"}</strong>
          </div>
          <div className="info-item">
            <span>Backup Directory</span>
            <strong>{backupDir || "-"}</strong>
          </div>
        </div>
        <div className="form-actions">
          <button type="button" onClick={createBackup} disabled={creating}>
            {creating ? "创建中" : "Create Backup"}
          </button>
        </div>
      </section>

      <section className="panel stack">
        <h2>Backup Files</h2>
        <DataTable
          headers={["文件", "大小", "创建时间", "SHA256", "操作"]}
          empty="暂无备份。"
          rows={backups.map((backup) => ({
            key: backup.filename,
            cells: [
              backup.filename,
              formatSize(backup.size_bytes),
              formatDate(backup.created_at),
              <code className="raw-json">{backup.sha256}</code>,
              <button className="secondary compact-button" type="button" onClick={() => setSelectedBackup(backup)}>
                Restore
              </button>,
            ],
          }))}
        />
      </section>

      {selectedBackup && (
        <form className="panel stack" onSubmit={restoreBackup}>
          <div className="section-heading">
            <div>
              <h2>Restore Confirmation</h2>
              <span className="subtle">{selectedBackup.filename}</span>
            </div>
          </div>
          <div className="fields">
            <label>
              <span>恢复原因</span>
              <textarea value={restoreReason} onChange={(event) => setRestoreReason(event.target.value)} />
            </label>
            <label>
              <span>输入 RESTORE 以确认</span>
              <input value={confirmationText} onChange={(event) => setConfirmationText(event.target.value)} />
            </label>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={confirmedImpact}
                onChange={(event) => setConfirmedImpact(event.target.checked)}
              />
              <span>我确认恢复会替换当前数据库文件，并会先生成 pre-restore backup。</span>
            </label>
          </div>
          <div className="form-actions">
            <button type="submit" disabled={!canRestore || restoring}>
              {restoring ? "恢复中" : "Restore"}
            </button>
            <button className="secondary" type="button" onClick={() => setSelectedBackup(null)}>
              取消
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
