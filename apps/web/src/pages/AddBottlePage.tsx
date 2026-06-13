import { FormEvent, useState } from "react";
import { api } from "../api";
import type { AppData } from "../types";
import { CheckboxInput, FormSection, Select, TextInput } from "../components/ui/FormControls";

export function AddBottlePage({
  data,
  afterMutation,
  openBottle,
}: {
  data: AppData;
  afterMutation: (message: string) => Promise<void>;
  openBottle: (id: string) => void;
}) {
  const [form, setForm] = useState({
    producerId: "",
    producerName: "",
    producerNameCn: "",
    producerCountry: "",
    producerRegion: "",
    wineId: "",
    wineName: "",
    wineNameCn: "",
    wineType: "red",
    wineCountry: "",
    wineRegion: "",
    vintageId: "",
    vintageYear: new Date().getFullYear().toString(),
    isNonVintage: false,
    drinkFrom: "",
    drinkTo: "",
    drinkConfidence: "",
    cellarId: "",
    cellarName: "",
    rows: "4",
    columns: "6",
    locationId: "",
    locationCode: "A-01-01",
    rowIndex: "1",
    columnIndex: "1",
    bottleSizeMl: "750",
    acquisitionDate: "",
    purchasePrice: "",
    purchaseCurrency: "CNY",
    purchaseSource: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wines = form.producerId ? data.wines.filter((wine) => wine.producer_id === form.producerId) : data.wines;
  const vintages = form.wineId ? data.vintages.filter((vintage) => vintage.wine_id === form.wineId) : data.vintages;
  const locations = form.cellarId ? data.locations.filter((location) => location.cellar_id === form.cellarId) : data.locations;

  function setField<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const producerId =
        form.producerId ||
        (
          await api.createProducer({
            name_original: form.producerName || "Unknown Producer",
            name_cn: form.producerNameCn || null,
            country: form.producerCountry || null,
            region: form.producerRegion || null,
          })
        ).id;
      const wineId =
        form.wineId ||
        (
          await api.createWine({
            producer_id: producerId,
            name_original: form.wineName || "Unknown Wine",
            name_cn: form.wineNameCn || null,
            type: form.wineType || null,
            country: form.wineCountry || form.producerCountry || null,
            region: form.wineRegion || form.producerRegion || null,
          })
        ).id;
      const vintageId =
        form.vintageId ||
        (
          await api.createVintage({
            wine_id: wineId,
            vintage_year: form.isNonVintage || !form.vintageYear ? null : Number(form.vintageYear),
            is_non_vintage: form.isNonVintage,
            default_drink_from: form.drinkFrom ? Number(form.drinkFrom) : null,
            default_drink_to: form.drinkTo ? Number(form.drinkTo) : null,
            drink_window_confidence: form.drinkConfidence || null,
          })
        ).id;
      const cellarId =
        form.cellarId ||
        (
          await api.createCellar({
            name: form.cellarName || "默认酒柜",
            cellar_type: "cabinet",
            rows: Number(form.rows) || null,
            columns: Number(form.columns) || null,
          })
        ).id;
      const locationId =
        form.locationId ||
        (
          await api.createLocation({
            cellar_id: cellarId,
            code: form.locationCode || "A-01-01",
            row_index: Number(form.rowIndex) || null,
            column_index: Number(form.columnIndex) || null,
            capacity: 1,
          })
        ).id;
      const bottle = await api.createBottle({
        vintage_id: vintageId,
        current_location_id: locationId,
        bottle_size_ml: Number(form.bottleSizeMl) || 750,
        acquisition_date: form.acquisitionDate || null,
        purchase_price: form.purchasePrice || null,
        purchase_currency: form.purchaseCurrency || "CNY",
        purchase_source: form.purchaseSource || null,
        personal_notes: form.notes || null,
        note: "前端手动入库",
      });
      await afterMutation("已入库");
      openBottle(bottle.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "新增入库失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="form-grid" onSubmit={submit}>
      <FormSection title="酒庄 / 酒款 / 年份">
        <Select label="选择酒庄" value={form.producerId} onChange={(value) => setField("producerId", value)} placeholder="新建酒庄" options={data.producers.map((item) => [item.id, item.name_cn || item.name_original])} />
        <TextInput label="新酒庄英文/原名" value={form.producerName} onChange={(value) => setField("producerName", value)} />
        <TextInput label="新酒庄中文名" value={form.producerNameCn} onChange={(value) => setField("producerNameCn", value)} />
        <TextInput label="酒庄国家" value={form.producerCountry} onChange={(value) => setField("producerCountry", value)} />
        <TextInput label="酒庄产区" value={form.producerRegion} onChange={(value) => setField("producerRegion", value)} />
        <Select label="选择酒款" value={form.wineId} onChange={(value) => setField("wineId", value)} placeholder="新建酒款" options={wines.map((item) => [item.id, item.name_cn || item.name_original])} />
        <TextInput label="新酒款英文/原名" value={form.wineName} onChange={(value) => setField("wineName", value)} />
        <TextInput label="新酒款中文名" value={form.wineNameCn} onChange={(value) => setField("wineNameCn", value)} />
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
        <TextInput label="酒款国家" value={form.wineCountry} onChange={(value) => setField("wineCountry", value)} />
        <TextInput label="酒款产区" value={form.wineRegion} onChange={(value) => setField("wineRegion", value)} />
        <Select label="选择年份" value={form.vintageId} onChange={(value) => setField("vintageId", value)} placeholder="新建年份" options={vintages.map((item) => [item.id, `${item.wine_name ?? "Wine"} ${item.is_non_vintage ? "NV" : item.vintage_year}`])} />
        <CheckboxInput label="无年份 / NV" checked={form.isNonVintage} onChange={(value) => setField("isNonVintage", value)} />
        <TextInput label="新年份" value={form.vintageYear} onChange={(value) => setField("vintageYear", value)} disabled={form.isNonVintage} />
        <TextInput label="适饮开始年" value={form.drinkFrom} onChange={(value) => setField("drinkFrom", value)} />
        <TextInput label="适饮结束年" value={form.drinkTo} onChange={(value) => setField("drinkTo", value)} />
        <Select
          label="适饮置信度"
          value={form.drinkConfidence}
          onChange={(value) => setField("drinkConfidence", value)}
          placeholder="未填写"
          options={[
            ["low", "低"],
            ["medium", "中"],
            ["high", "高"],
          ]}
        />
      </FormSection>
      <FormSection title="酒柜 / 位置">
        <Select label="选择酒柜" value={form.cellarId} onChange={(value) => setField("cellarId", value)} placeholder="新建酒柜" options={data.cellars.map((item) => [item.id, item.name])} />
        <TextInput label="新酒柜名称" value={form.cellarName} onChange={(value) => setField("cellarName", value)} />
        <TextInput label="行数" value={form.rows} onChange={(value) => setField("rows", value)} />
        <TextInput label="列数" value={form.columns} onChange={(value) => setField("columns", value)} />
        <Select label="选择位置" value={form.locationId} onChange={(value) => setField("locationId", value)} placeholder="新建位置" options={locations.map((item) => [item.id, `${item.cellar_name ?? ""} ${item.code}`])} />
        <TextInput label="新位置编码" value={form.locationCode} onChange={(value) => setField("locationCode", value)} />
        <TextInput label="行" value={form.rowIndex} onChange={(value) => setField("rowIndex", value)} />
        <TextInput label="列" value={form.columnIndex} onChange={(value) => setField("columnIndex", value)} />
      </FormSection>
      <FormSection title="单瓶信息">
        <TextInput label="容量 ml" value={form.bottleSizeMl} onChange={(value) => setField("bottleSizeMl", value)} />
        <TextInput label="购入日期" value={form.acquisitionDate} onChange={(value) => setField("acquisitionDate", value)} placeholder="YYYY-MM-DD" />
        <TextInput label="购买价" value={form.purchasePrice} onChange={(value) => setField("purchasePrice", value)} />
        <TextInput label="币种" value={form.purchaseCurrency} onChange={(value) => setField("purchaseCurrency", value)} />
        <TextInput label="购买来源" value={form.purchaseSource} onChange={(value) => setField("purchaseSource", value)} />
        <TextInput label="备注" value={form.notes} onChange={(value) => setField("notes", value)} />
      </FormSection>
      <div className="form-actions">
        <button type="submit" disabled={submitting}>{submitting ? "保存中" : "确认入库"}</button>
        {error && <div className="inline-error">{error}</div>}
      </div>
    </form>
  );
}
