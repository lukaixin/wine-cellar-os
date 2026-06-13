import { statusLabel } from "../../domain/constants";

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`status-badge ${status === "in_stock" ? "available" : "unavailable"}`}>
      {statusLabel[status] ?? status}
    </span>
  );
}
