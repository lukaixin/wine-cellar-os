import { drinkWindowStatusLabel } from "../domain/constants";
import type { Bottle, InventoryTransaction, Location } from "../types";

export function normalize(value: unknown): string {
  return String(value ?? "").toLowerCase().trim();
}

export function bottleTitle(bottle: Bottle): string {
  const producer = bottle.producer_name_cn || bottle.producer_name || "未知酒庄";
  const wine = bottle.wine_name_cn || bottle.wine_name || "未知酒款";
  return `${producer} · ${wine} · ${formatVintage(bottle)}`;
}

export function formatVintage(bottle: Bottle): string {
  return bottle.is_non_vintage ? "NV" : String(bottle.vintage_year ?? "未知年份");
}

export function formatLocation(bottle: Bottle): string {
  return [bottle.cellar_name, bottle.location_code].filter(Boolean).join(" / ") || "无位置";
}

export function formatDrinkWindow(bottle: Bottle): string {
  if (!bottle.default_drink_from || !bottle.default_drink_to) return "未设置";
  return `${bottle.default_drink_from}-${bottle.default_drink_to}`;
}

export function formatDrinkWindowStatus(bottle: Bottle): string {
  const status = bottle.drink_window_status ?? "UNKNOWN";
  return drinkWindowStatusLabel[status] ?? status;
}

export function formatPrice(bottle: Bottle): string {
  if (!bottle.purchase_price) return "-";
  return `${bottle.purchase_currency || "CNY"} ${bottle.purchase_price}`;
}

export function isBottleAvailable(bottle: Bottle): boolean {
  return bottle.current_status === "in_stock";
}

export function bottleLocationIssue(bottle: Bottle, locations: Location[]): string | null {
  if (bottle.current_status === "in_stock" && !bottle.current_location_id) {
    return "在库但缺少位置";
  }
  if (bottle.current_status === "in_stock" && !locations.some((location) => location.id === bottle.current_location_id)) {
    return "在库位置不存在";
  }
  if (bottle.current_status !== "in_stock" && bottle.current_location_id) {
    return "非在库但仍有关联位置";
  }
  return null;
}

export function sortByOccurredAtAsc(transactions: InventoryTransaction[]): InventoryTransaction[] {
  return [...transactions].sort((left, right) => new Date(left.occurred_at).getTime() - new Date(right.occurred_at).getTime());
}

export function countByLocation(bottles: Bottle[]): Map<string, Bottle[]> {
  const map = new Map<string, Bottle[]>();
  for (const bottle of bottles) {
    if (bottle.current_status !== "in_stock" || !bottle.current_location_id) continue;
    map.set(bottle.current_location_id, [...(map.get(bottle.current_location_id) ?? []), bottle]);
  }
  return map;
}
