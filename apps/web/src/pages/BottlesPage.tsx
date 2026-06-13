import { useMemo, useState } from "react";
import { drinkWindowStatusLabel, statusLabel } from "../domain/constants";
import type { AppData } from "../types";
import { formatDrinkWindow, formatLocation, formatPrice, formatVintage, normalize } from "../utils/wine";
import { DataTable } from "../components/ui/DataTable";
import { DrinkWindowBadge } from "../components/ui/DrinkWindowBadge";
import { Select, TextInput } from "../components/ui/FormControls";
import { StatusBadge } from "../components/ui/StatusBadge";

export function BottlesPage({ data, openBottle }: { data: AppData; openBottle: (id: string) => void }) {
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [locationFilter, setLocationFilter] = useState("");
  const filtered = useMemo(() => {
    const keyword = normalize(query);
    return data.bottles.filter((bottle) => {
      const haystack = normalize([
        bottle.producer_name,
        bottle.producer_name_cn,
        bottle.wine_name,
        bottle.wine_name_cn,
        bottle.vintage_year,
        bottle.current_status,
        statusLabel[bottle.current_status],
        bottle.drink_window_status,
        drinkWindowStatusLabel[bottle.drink_window_status ?? "UNKNOWN"],
        bottle.cellar_name,
        bottle.location_code,
        bottle.country,
        bottle.wine_type,
        bottle.personal_notes,
      ].join(" "));
      const matchesQuery = !keyword || haystack.includes(keyword);
      const matchesStatus = !statusFilter || bottle.current_status === statusFilter;
      const matchesLocation = !locationFilter || bottle.current_location_id === locationFilter;
      return matchesQuery && matchesStatus && matchesLocation;
    });
  }, [data.bottles, locationFilter, query, statusFilter]);

  const statuses = Array.from(new Set(data.bottles.map((bottle) => bottle.current_status))).sort();

  return (
    <section className="stack">
      <section className="panel filter-panel">
        <div className="filter-bar">
          <TextInput label="搜索" value={query} onChange={setQuery} placeholder="酒庄、酒款、年份、状态、位置" />
          <Select
            label="状态"
            value={statusFilter}
            onChange={setStatusFilter}
            placeholder="全部状态"
            options={statuses.map((status) => [status, statusLabel[status] ?? status])}
          />
          <Select
            label="位置"
            value={locationFilter}
            onChange={setLocationFilter}
            placeholder="全部位置"
            options={data.locations.map((item) => [item.id, `${item.cellar_name ?? ""} ${item.code}`])}
          />
        </div>
        <div className="subtle">共 {filtered.length} / {data.bottles.length} 瓶</div>
      </section>
      <section className="panel">
        <DataTable
          headers={["酒庄", "酒款", "年份", "库存状态", "位置", "适饮状态", "适饮期", "价格"]}
          empty={data.bottles.length ? "没有匹配的藏酒。" : "暂无藏酒。"}
          rows={filtered.map((bottle) => ({
            key: bottle.id,
            onClick: () => openBottle(bottle.id),
            cells: [
              bottle.producer_name_cn || bottle.producer_name || "未知",
              bottle.wine_name_cn || bottle.wine_name || "未知",
              formatVintage(bottle),
              <StatusBadge key="status" status={bottle.current_status} />,
              formatLocation(bottle),
              <DrinkWindowBadge key="drink-window" status={bottle.drink_window_status} />,
              formatDrinkWindow(bottle),
              formatPrice(bottle),
            ],
          }))}
        />
      </section>
    </section>
  );
}
