import { transactionLabel } from "../../domain/constants";
import type { InventoryTransaction } from "../../types";

export function TransactionTimeline({ transactions }: { transactions: InventoryTransaction[] }) {
  if (!transactions.length) {
    return <div className="empty">暂无记录。</div>;
  }
  return (
    <ol className="timeline">
      {transactions.map((item) => (
        <li key={item.id}>
          <div className="timeline-dot" />
          <div className="timeline-card">
            <div className="timeline-top">
              <strong>{transactionLabel[item.transaction_type] ?? item.transaction_type}</strong>
              <span>{new Date(item.occurred_at).toLocaleString("zh-CN")}</span>
            </div>
            <div className="subtle">
              {[item.from_location_code && `从 ${item.from_location_code}`, item.to_location_code && `到 ${item.to_location_code}`]
                .filter(Boolean)
                .join(" / ") || "无位置变化"}
            </div>
            {item.note && <p>{item.note}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}
