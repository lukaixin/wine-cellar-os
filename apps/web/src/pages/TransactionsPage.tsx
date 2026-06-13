import { FormEvent, useEffect, useState } from "react";
import { api } from "../api";
import { transactionLabel, type BottleAction } from "../domain/constants";
import type { AppData, Bottle, Location } from "../types";
import { bottleTitle, isBottleAvailable } from "../utils/wine";
import { TransactionTable } from "../components/transactions/TransactionTable";
import { Select, TextInput } from "../components/ui/FormControls";

export function TransactionsPage({ data, afterMutation }: { data: AppData; afterMutation: (message: string) => Promise<void> }) {
  return (
    <section className="stack">
      <TransactionForm bottles={data.bottles} locations={data.locations} afterMutation={afterMutation} />
      <section className="panel">
        <h2>Transaction</h2>
        <TransactionTable transactions={data.transactions} />
      </section>
    </section>
  );
}

function TransactionForm({
  bottles,
  locations,
  afterMutation,
}: {
  bottles: Bottle[];
  locations: Location[];
  afterMutation: (message: string) => Promise<void>;
}) {
  const [bottleId, setBottleId] = useState(bottles[0]?.id ?? "");
  const [type, setType] = useState<BottleAction>("MOVE");
  const [toLocationId, setToLocationId] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const selectedBottle = bottles.find((bottle) => bottle.id === bottleId);

  useEffect(() => {
    if (!bottleId && bottles[0]?.id) setBottleId(bottles[0].id);
  }, [bottleId, bottles]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!selectedBottle) {
      setError("请选择酒瓶。");
      return;
    }
    if (type !== "ADJUST" && !isBottleAvailable(selectedBottle)) {
      setError("当前酒瓶已不可用，不能再次出库。");
      return;
    }
    if (type === "MOVE" && !toLocationId) {
      setError("移动必须选择目标位置。");
      return;
    }
    if (type === "MOVE" && toLocationId === selectedBottle.current_location_id) {
      setError("目标位置不能和当前位置相同。");
      return;
    }
    if (type === "ADJUST" && !note.trim()) {
      setError("盘点调整必须填写备注。");
      return;
    }
    try {
      await api.createTransaction({
        bottle_id: bottleId,
        transaction_type: type,
        from_location_id: selectedBottle.current_location_id ?? null,
        to_location_id: ["MOVE", "ADJUST"].includes(type) && toLocationId ? toLocationId : null,
        note: note || null,
      });
      setNote("");
      setToLocationId("");
      await afterMutation("Transaction 已记录");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Transaction 保存失败");
    }
  }

  return (
    <form className="panel form-row" onSubmit={submit}>
      <h2>记录 Transaction</h2>
      <Select label="酒瓶" value={bottleId} onChange={setBottleId} placeholder="选择酒瓶" options={bottles.map((item) => [item.id, bottleTitle(item)])} />
      <Select
        label="类型"
        value={type}
        onChange={(value) => setType(value as BottleAction)}
        options={(["MOVE", "CONSUME", "GIFT", "DAMAGE", "ADJUST"] as BottleAction[]).map((item) => [item, transactionLabel[item]])}
      />
      <Select label="目标位置" value={toLocationId} onChange={setToLocationId} placeholder="不选择" options={locations.map((item) => [item.id, `${item.cellar_name ?? ""} ${item.code}`])} />
      <TextInput label="备注" value={note} onChange={setNote} />
      <button type="submit" disabled={!bottleId}>保存</button>
      {error && <div className="inline-error">{error}</div>}
    </form>
  );
}
