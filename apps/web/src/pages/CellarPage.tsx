import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { statusLabel } from "../domain/constants";
import type { AppData, Cellar } from "../types";
import { bottleLocationIssue, bottleTitle, countByLocation } from "../utils/wine";
import { DataTable } from "../components/ui/DataTable";
import { EmptyPanel } from "../components/ui/EmptyPanel";
import { Select, TextInput } from "../components/ui/FormControls";

export function CellarPage({
  data,
  openBottle,
  afterMutation,
}: {
  data: AppData;
  openBottle: (id: string) => void;
  afterMutation: (message: string) => Promise<void>;
}) {
  const [cellarId, setCellarId] = useState(data.cellars[0]?.id ?? "");
  const [selectedLocationId, setSelectedLocationId] = useState<string | null>(null);
  const cellar = data.cellars.find((item) => item.id === cellarId) ?? data.cellars[0];
  const activeCellarId = cellar?.id ?? "";
  const locations = data.locations.filter((item) => item.cellar_id === activeCellarId);
  const selectedLocation = locations.find((item) => item.id === selectedLocationId) ?? locations[0];
  const bottlesByLocation = countByLocation(data.bottles);
  const locationIssues = data.bottles
    .map((bottle) => ({ bottle, issue: bottleLocationIssue(bottle, data.locations) }))
    .filter((item): item is { bottle: AppData["bottles"][number]; issue: string } => Boolean(item.issue));
  const rows = cellar?.rows ?? Math.max(1, ...locations.map((item) => item.row_index ?? 1));
  const columns = cellar?.columns ?? Math.max(1, ...locations.map((item) => item.column_index ?? 1));

  useEffect(() => {
    if (!cellarId && data.cellars[0]?.id) {
      setCellarId(data.cellars[0].id);
    }
  }, [cellarId, data.cellars]);

  return (
    <section className="stack">
      <div className="toolbar">
        <Select
          label="当前酒柜"
          value={activeCellarId}
          onChange={(value) => {
            setCellarId(value);
            setSelectedLocationId(null);
          }}
          placeholder="选择酒柜"
          options={data.cellars.map((item) => [item.id, item.name])}
        />
      </div>
      <CellarManager
        cellar={cellar}
        afterMutation={afterMutation}
        onCellarSelected={(id) => setCellarId(id)}
      />
      {cellar ? (
        <>
          <div className="grid-board" style={{ gridTemplateColumns: `repeat(${Math.max(columns, 1)}, minmax(92px, 1fr))` }}>
            {Array.from({ length: Math.max(rows, 1) * Math.max(columns, 1) }, (_, index) => {
              const row = Math.floor(index / Math.max(columns, 1)) + 1;
              const column = (index % Math.max(columns, 1)) + 1;
              const location = locations.find((item) => item.row_index === row && item.column_index === column);
              const bottles = location ? bottlesByLocation.get(location.id) ?? [] : [];
              const overCapacity = location ? bottles.length > location.capacity : false;
              const cellClass = [
                "grid-cell",
                bottles.length ? "occupied" : "empty-location",
                location && selectedLocation?.id === location.id ? "selected" : "",
                location ? "" : "missing-location",
                overCapacity ? "over-capacity" : "",
              ].filter(Boolean).join(" ");
              return (
                <div key={`${row}-${column}`} className={cellClass} onClick={() => location && setSelectedLocationId(location.id)}>
                  <strong>{location?.code ?? `${row}-${column}`}</strong>
                  <small>{location ? (bottles.length ? `占用 ${bottles.length}/${location.capacity}` : "空位") : "未建位置"}</small>
                  {bottles.map((bottle) => (
                    <button key={bottle.id} onClick={(event) => { event.stopPropagation(); openBottle(bottle.id); }}>
                      {bottle.wine_name_cn || bottle.wine_name || "酒"}
                    </button>
                  ))}
                </div>
              );
            })}
          </div>
          <div className="two-column">
            <section className="panel">
              <h2>位置详情</h2>
              {selectedLocation ? (
                <div className="location-detail">
                  <div className="status-row">
                    <span>{selectedLocation.code}</span>
                    <strong>{bottlesByLocation.get(selectedLocation.id)?.length ?? 0}/{selectedLocation.capacity}</strong>
                  </div>
                  <div className="compact-list">
                    {(bottlesByLocation.get(selectedLocation.id) ?? []).map((bottle) => (
                      <button key={bottle.id} onClick={() => openBottle(bottle.id)}>
                        <span>{bottleTitle(bottle)}</span>
                        <small>{statusLabel[bottle.current_status] ?? bottle.current_status}</small>
                      </button>
                    ))}
                    {!(bottlesByLocation.get(selectedLocation.id) ?? []).length && <div className="empty">这个位置目前为空。</div>}
                  </div>
                </div>
              ) : (
                <div className="empty">暂无可查看的位置。</div>
              )}
            </section>
            <section className="panel">
              <h2>位置异常</h2>
              {locationIssues.length ? (
                <div className="issue-list">
                  {locationIssues.map(({ bottle, issue }) => (
                    <button className="issue-item" key={bottle.id} onClick={() => openBottle(bottle.id)}>
                      <span>{bottleTitle(bottle)}</span>
                      <small>{issue}</small>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="empty">没有发现位置异常。</div>
              )}
            </section>
          </div>
          <section className="panel">
            <h2>位置列表</h2>
            <DataTable
              headers={["编码", "行", "列", "容量", "当前瓶数"]}
              empty="暂无位置。"
              rows={locations.map((location) => ({
                key: location.id,
                cells: [
                  location.code,
                  location.row_index ?? "-",
                  location.column_index ?? "-",
                  location.capacity,
                  bottlesByLocation.get(location.id)?.length ?? 0,
                ],
              }))}
            />
          </section>
        </>
      ) : (
        <EmptyPanel title="还没有酒柜" text="先创建一个酒柜，再批量生成位置。" />
      )}
    </section>
  );
}

function CellarManager({
  cellar,
  afterMutation,
  onCellarSelected,
}: {
  cellar?: Cellar;
  afterMutation: (message: string) => Promise<void>;
  onCellarSelected: (id: string) => void;
}) {
  const [createForm, setCreateForm] = useState({ name: "", cellarType: "cabinet", rows: "4", columns: "6" });
  const [editForm, setEditForm] = useState({ name: cellar?.name ?? "", cellarType: cellar?.cellar_type ?? "cabinet", rows: String(cellar?.rows ?? ""), columns: String(cellar?.columns ?? "") });
  const [batchForm, setBatchForm] = useState({ rows: "4", columns: "6", codePrefix: "A", capacity: "1" });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEditForm({
      name: cellar?.name ?? "",
      cellarType: cellar?.cellar_type ?? "cabinet",
      rows: String(cellar?.rows ?? ""),
      columns: String(cellar?.columns ?? ""),
    });
  }, [cellar]);

  async function createCellar(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      const created = await api.createCellar({
        name: createForm.name || "新酒柜",
        cellar_type: createForm.cellarType || "cabinet",
        rows: Number(createForm.rows) || null,
        columns: Number(createForm.columns) || null,
      });
      onCellarSelected(created.id);
      setCreateForm({ name: "", cellarType: "cabinet", rows: "4", columns: "6" });
      await afterMutation("酒柜已创建");
    } catch (err) {
      setError(err instanceof Error ? err.message : "创建酒柜失败");
    }
  }

  async function updateCellar(event: FormEvent) {
    event.preventDefault();
    if (!cellar) return;
    setError(null);
    try {
      await api.updateCellar(cellar.id, {
        name: editForm.name || cellar.name,
        cellar_type: editForm.cellarType || cellar.cellar_type,
        rows: Number(editForm.rows) || null,
        columns: Number(editForm.columns) || null,
      });
      await afterMutation("酒柜已更新");
    } catch (err) {
      setError(err instanceof Error ? err.message : "更新酒柜失败");
    }
  }

  async function batchCreate(event: FormEvent) {
    event.preventDefault();
    if (!cellar) return;
    setError(null);
    try {
      await api.batchCreateLocations(cellar.id, {
        rows: Number(batchForm.rows) || 1,
        columns: Number(batchForm.columns) || 1,
        code_prefix: batchForm.codePrefix || "A",
        capacity: Number(batchForm.capacity) || 1,
      });
      await afterMutation("位置已生成");
    } catch (err) {
      setError(err instanceof Error ? err.message : "生成位置失败");
    }
  }

  return (
    <section className="panel cellar-manager">
      <h2>酒柜管理</h2>
      <div className="manager-grid">
        <form className="mini-form" onSubmit={createCellar}>
          <h3>创建酒柜</h3>
          <TextInput label="名称" value={createForm.name} onChange={(value) => setCreateForm((current) => ({ ...current, name: value }))} />
          <TextInput label="类型" value={createForm.cellarType} onChange={(value) => setCreateForm((current) => ({ ...current, cellarType: value }))} />
          <TextInput label="行数" value={createForm.rows} onChange={(value) => setCreateForm((current) => ({ ...current, rows: value }))} />
          <TextInput label="列数" value={createForm.columns} onChange={(value) => setCreateForm((current) => ({ ...current, columns: value }))} />
          <button type="submit">创建</button>
        </form>
        <form className="mini-form" onSubmit={updateCellar}>
          <h3>编辑当前酒柜</h3>
          <TextInput label="名称" value={editForm.name} onChange={(value) => setEditForm((current) => ({ ...current, name: value }))} disabled={!cellar} />
          <TextInput label="类型" value={editForm.cellarType} onChange={(value) => setEditForm((current) => ({ ...current, cellarType: value }))} disabled={!cellar} />
          <TextInput label="行数" value={editForm.rows} onChange={(value) => setEditForm((current) => ({ ...current, rows: value }))} disabled={!cellar} />
          <TextInput label="列数" value={editForm.columns} onChange={(value) => setEditForm((current) => ({ ...current, columns: value }))} disabled={!cellar} />
          <button type="submit" disabled={!cellar}>保存</button>
        </form>
        <form className="mini-form" onSubmit={batchCreate}>
          <h3>批量生成位置</h3>
          <TextInput label="行数" value={batchForm.rows} onChange={(value) => setBatchForm((current) => ({ ...current, rows: value }))} disabled={!cellar} />
          <TextInput label="列数" value={batchForm.columns} onChange={(value) => setBatchForm((current) => ({ ...current, columns: value }))} disabled={!cellar} />
          <TextInput label="编码前缀" value={batchForm.codePrefix} onChange={(value) => setBatchForm((current) => ({ ...current, codePrefix: value }))} disabled={!cellar} />
          <TextInput label="单格容量" value={batchForm.capacity} onChange={(value) => setBatchForm((current) => ({ ...current, capacity: value }))} disabled={!cellar} />
          <button type="submit" disabled={!cellar}>生成位置</button>
        </form>
      </div>
      {error && <div className="inline-error">{error}</div>}
    </section>
  );
}
