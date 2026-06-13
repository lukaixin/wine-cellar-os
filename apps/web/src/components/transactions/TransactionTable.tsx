import { transactionLabel } from "../../domain/constants";
import type { InventoryTransaction } from "../../types";
import { DataTable } from "../ui/DataTable";

export function TransactionTable({ transactions, compact = false }: { transactions: InventoryTransaction[]; compact?: boolean }) {
  return (
    <DataTable
      headers={compact ? ["类型", "酒", "位置", "时间"] : ["类型", "酒", "原位置", "目标位置", "备注", "时间"]}
      empty="暂无记录。"
      rows={transactions.map((item) => ({
        key: item.id,
        cells: compact
          ? [
              transactionLabel[item.transaction_type] ?? item.transaction_type,
              item.bottle_label ?? item.bottle_id.slice(0, 8),
              item.to_location_code || item.from_location_code || "-",
              new Date(item.occurred_at).toLocaleString("zh-CN"),
            ]
          : [
              transactionLabel[item.transaction_type] ?? item.transaction_type,
              item.bottle_label ?? item.bottle_id.slice(0, 8),
              item.from_location_code ?? "-",
              item.to_location_code ?? "-",
              item.note ?? "-",
              new Date(item.occurred_at).toLocaleString("zh-CN"),
            ],
      }))}
    />
  );
}
