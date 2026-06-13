import { drinkWindowStatusLabel } from "../../domain/constants";
import type { DrinkWindowStatus } from "../../types";

export function DrinkWindowBadge({ status }: { status?: DrinkWindowStatus | null }) {
  const value = status ?? "UNKNOWN";
  return <span className={`drink-window-badge ${value.toLowerCase()}`}>{drinkWindowStatusLabel[value] ?? value}</span>;
}
