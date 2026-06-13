import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { transactionLabel, type BottleAction } from "../domain/constants";
import type { Bottle, InventoryTransaction, Location } from "../types";
import {
  bottleLocationIssue,
  bottleTitle,
  formatDrinkWindow,
  formatLocation,
  formatPrice,
  isBottleAvailable,
  sortByOccurredAtAsc,
} from "../utils/wine";
import { TransactionTimeline } from "../components/transactions/TransactionTimeline";
import { Select, TextInput } from "../components/ui/FormControls";
import { InfoItem } from "../components/ui/InfoItem";
import { StatusBadge } from "../components/ui/StatusBadge";

export function BottleDetailPage({
  bottle,
  locations,
  transactions,
  afterMutation,
}: {
  bottle: Bottle;
  locations: Location[];
  transactions: InventoryTransaction[];
  afterMutation: (message: string) => Promise<void>;
}) {
  const issue = bottleLocationIssue(bottle, locations);
  return (
    <section className="stack">
      <div className="detail-header">
        <div>
          <h2>{bottleTitle(bottle)}</h2>
          <p>{formatLocation(bottle)}</p>
        </div>
        <div className="status-cluster">
          <StatusBadge status={bottle.current_status} />
          <span className="pill">{bottle.bottle_size_ml}ml</span>
        </div>
      </div>
      {issue && <div className="banner warning">{issue}</div>}
      <section className="panel">
        <h2>酒瓶信息</h2>
        <div className="detail-grid">
          <InfoItem label="国家/产区" value={bottle.country || "-"} />
          <InfoItem label="类型" value={bottle.wine_type || "-"} />
          <InfoItem label="适饮期" value={formatDrinkWindow(bottle)} />
          <InfoItem label="适饮置信度" value={bottle.drink_window_confidence || "-"} />
          <InfoItem label="购入日期" value={bottle.acquisition_date || "-"} />
          <InfoItem label="购入价格" value={formatPrice(bottle)} />
          <InfoItem label="购买来源" value={bottle.purchase_source || "-"} />
          <InfoItem label="备注" value={bottle.personal_notes || "-"} />
        </div>
      </section>
      <BottleActionPanel bottle={bottle} locations={locations} afterMutation={afterMutation} />
      <section className="panel">
        <h2>完整 Transaction 时间线</h2>
        <TransactionTimeline transactions={sortByOccurredAtAsc(transactions)} />
      </section>
    </section>
  );
}

function BottleActionPanel({
  bottle,
  locations,
  afterMutation,
}: {
  bottle: Bottle;
  locations: Location[];
  afterMutation: (message: string) => Promise<void>;
}) {
  const [action, setAction] = useState<BottleAction>("MOVE");
  const [toLocationId, setToLocationId] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const available = isBottleAvailable(bottle);
  const targetRequired = action === "MOVE";
  const targetAllowed = action === "MOVE" || action === "ADJUST";
  const noteRequired = action === "ADJUST";
  const unavailableAction = !available && action !== "ADJUST";

  useEffect(() => {
    if (!available && action !== "ADJUST") {
      setAction("ADJUST");
    }
  }, [action, available]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (unavailableAction) {
      setError("当前酒瓶已不可用，只能做盘点调整。");
      return;
    }
    if (targetRequired && !toLocationId) {
      setError("移动必须选择目标位置。");
      return;
    }
    if (action === "MOVE" && toLocationId === bottle.current_location_id) {
      setError("目标位置不能和当前位置相同。");
      return;
    }
    if (noteRequired && !note.trim()) {
      setError("盘点调整必须填写备注。");
      return;
    }

    setSubmitting(true);
    try {
      await api.createTransaction({
        bottle_id: bottle.id,
        transaction_type: action,
        from_location_id: bottle.current_location_id ?? null,
        to_location_id: targetAllowed && toLocationId ? toLocationId : null,
        note: note.trim() || null,
      });
      setNote("");
      setToLocationId("");
      await afterMutation(`${transactionLabel[action]}已记录`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transaction 保存失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="panel action-panel" onSubmit={submit}>
      <div className="action-header">
        <h2>库存操作</h2>
        {!available && <span className="subtle">已不可用的酒瓶禁止再次饮用、送礼或损耗。</span>}
      </div>
      <div className="action-buttons">
        {(["MOVE", "CONSUME", "GIFT", "DAMAGE", "ADJUST"] as BottleAction[]).map((item) => (
          <button
            className={action === item ? "active-action" : "secondary"}
            disabled={!available && item !== "ADJUST"}
            key={item}
            onClick={() => {
              setAction(item);
              setError(null);
            }}
            type="button"
          >
            {transactionLabel[item]}
          </button>
        ))}
      </div>
      <div className="action-fields">
        {targetAllowed && (
          <Select
            label={action === "MOVE" ? "目标位置" : "调整后位置（留空则标记盘亏）"}
            value={toLocationId}
            onChange={setToLocationId}
            placeholder="选择位置"
            options={locations.map((item) => [item.id, `${item.cellar_name ?? ""} ${item.code}`])}
          />
        )}
        <TextInput label={noteRequired ? "备注（必填）" : "备注"} value={note} onChange={setNote} />
        <button type="submit" disabled={submitting || unavailableAction}>
          {submitting ? "保存中" : `确认${transactionLabel[action]}`}
        </button>
      </div>
      {error && <div className="inline-error">{error}</div>}
    </form>
  );
}
