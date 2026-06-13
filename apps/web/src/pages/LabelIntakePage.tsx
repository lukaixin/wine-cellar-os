import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import type { AppData, LabelDraft } from "../types";
import { Select, TextInput } from "../components/ui/FormControls";

export function LabelIntakePage({
  data,
  afterMutation,
  openBottle,
}: {
  data: AppData;
  afterMutation: (message: string) => Promise<void>;
  openBottle: (id: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState("");
  const [draft, setDraft] = useState<LabelDraft | null>(null);
  const [form, setForm] = useState({
    producerName: "",
    wineName: "",
    vintageYear: "",
    country: "",
    region: "",
    wineType: "red",
    bottleSizeMl: "750",
    notes: "",
    cellarId: data.cellars[0]?.id ?? "",
    locationId: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const locations = form.cellarId ? data.locations.filter((location) => location.cellar_id === form.cellarId) : data.locations;

  useEffect(() => {
    return () => {
      if (previewUrl && typeof URL.revokeObjectURL === "function") {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!form.cellarId && data.cellars[0]?.id) {
      setForm((current) => ({ ...current, cellarId: data.cellars[0].id }));
    }
  }, [data.cellars, form.cellarId]);

  function setField<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  function handleFileChange(event: FormEvent<HTMLInputElement>) {
    const selected = event.currentTarget.files?.[0] ?? null;
    setFile(selected);
    setDraft(null);
    setError(null);
    if (previewUrl && typeof URL.revokeObjectURL === "function") {
      URL.revokeObjectURL(previewUrl);
    }
    setPreviewUrl(selected && typeof URL.createObjectURL === "function" ? URL.createObjectURL(selected) : "");
  }

  async function createDraft(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("请先选择 jpg、png 或 webp 酒标图片。");
      return;
    }
    setError(null);
    setUploading(true);
    try {
      const upload = await api.uploadLabelImage(file);
      const result = await api.createLabelDraft(upload.id);
      const candidate = result.candidate_fields;
      setDraft(result);
      setForm((current) => ({
        ...current,
        producerName: candidate.producer_name ?? "",
        wineName: candidate.wine_name ?? "",
        vintageYear: candidate.vintage_year ? String(candidate.vintage_year) : "",
        country: candidate.country ?? "",
        region: candidate.region ?? "",
        wineType: candidate.type ?? current.wineType,
        bottleSizeMl: candidate.bottle_size_ml ? String(candidate.bottle_size_ml) : "750",
        notes: candidate.notes ?? "",
      }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "酒标草稿生成失败");
    } finally {
      setUploading(false);
    }
  }

  async function confirmDraft(event: FormEvent) {
    event.preventDefault();
    if (!draft) {
      setError("请先生成草稿。");
      return;
    }
    if (!form.producerName.trim() || !form.wineName.trim()) {
      setError("酒庄和酒款必须填写。");
      return;
    }
    if (!Number(form.vintageYear)) {
      setError("年份必须填写为数字。");
      return;
    }
    if (!form.locationId) {
      setError("确认入库前必须选择酒柜位置。");
      return;
    }
    setError(null);
    setConfirming(true);
    try {
      const result = await api.confirmLabelDraft({
        upload_id: draft.upload.id,
        producer_name: form.producerName.trim(),
        wine_name: form.wineName.trim(),
        vintage_year: Number(form.vintageYear),
        bottle_size_ml: Number(form.bottleSizeMl) || 750,
        location_id: form.locationId,
        country: form.country.trim() || null,
        region: form.region.trim() || null,
        type: form.wineType || null,
        notes: form.notes.trim() || null,
      });
      await afterMutation("酒标草稿已确认入库");
      openBottle(result.bottle_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "酒标确认入库失败");
    } finally {
      setConfirming(false);
    }
  }

  return (
    <section className="stack">
      <div className="two-column label-intake-layout">
        <form className="panel label-upload-panel" onSubmit={createDraft}>
          <h2>上传酒标</h2>
          <label>
            <span>酒标图片</span>
            <input accept="image/jpeg,image/png,image/webp" type="file" onChange={handleFileChange} />
          </label>
          {previewUrl ? (
            <img className="label-preview" src={previewUrl} alt="酒标预览" />
          ) : (
            <div className="label-preview empty">本地预览</div>
          )}
          <button type="submit" disabled={uploading || !file}>
            {uploading ? "生成中" : "生成草稿"}
          </button>
          <div className="subtle">草稿识别只用于预填字段，确认前不会改变正式库存。</div>
        </form>

        <form className="panel label-draft-panel" onSubmit={confirmDraft}>
          <h2>确认草稿</h2>
          {!draft ? (
            <div className="empty">上传酒标并生成草稿后，在这里编辑字段并确认入库。</div>
          ) : (
            <>
              <div className="status-row">
                <span>{draft.recognizer}</span>
                <strong>{draft.confidence}</strong>
              </div>
              {draft.warnings.length > 0 && <div className="banner warning">{draft.warnings.join("; ")}</div>}
              <div className="fields">
                <TextInput label="酒庄" value={form.producerName} onChange={(value) => setField("producerName", value)} />
                <TextInput label="酒款" value={form.wineName} onChange={(value) => setField("wineName", value)} />
                <TextInput label="年份" value={form.vintageYear} onChange={(value) => setField("vintageYear", value)} />
                <TextInput label="容量 ml" value={form.bottleSizeMl} onChange={(value) => setField("bottleSizeMl", value)} />
                <TextInput label="国家" value={form.country} onChange={(value) => setField("country", value)} />
                <TextInput label="产区" value={form.region} onChange={(value) => setField("region", value)} />
                <Select
                  label="酒款类型"
                  value={form.wineType}
                  onChange={(value) => setField("wineType", value)}
                  placeholder="未填写"
                  options={[
                    ["red", "红葡萄酒"],
                    ["white", "白葡萄酒"],
                    ["sparkling", "起泡酒"],
                    ["sweet", "甜酒"],
                    ["fortified", "加强酒"],
                  ]}
                />
                <Select
                  label="酒柜"
                  value={form.cellarId}
                  onChange={(value) => setForm((current) => ({ ...current, cellarId: value, locationId: "" }))}
                  placeholder="选择酒柜"
                  options={data.cellars.map((item) => [item.id, item.name])}
                />
                <Select
                  label="入库位置"
                  value={form.locationId}
                  onChange={(value) => setField("locationId", value)}
                  placeholder="选择位置"
                  options={locations.map((item) => [item.id, `${item.cellar_name ?? ""} ${item.code}`])}
                />
                <TextInput label="备注" value={form.notes} onChange={(value) => setField("notes", value)} />
              </div>
              <div className="form-actions">
                <button type="submit" disabled={confirming || !draft}>
                  {confirming ? "入库中" : "确认入库"}
                </button>
              </div>
            </>
          )}
        </form>
      </div>
      {error && <div className="banner error">{error}</div>}
    </section>
  );
}
