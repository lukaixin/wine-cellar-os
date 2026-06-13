import { drinkWindowLabel, statusLabel } from "../domain/constants";
import type { AppData } from "../types";
import { bottleTitle, formatLocation } from "../utils/wine";
import { TransactionTable } from "../components/transactions/TransactionTable";
import { Metric, SummaryList } from "../components/ui/Summary";

export function DashboardPage({ data, openBottle }: { data: AppData; openBottle: (id: string) => void }) {
  const summary = data.dashboard;
  const latestBottles = [...data.bottles].sort((left, right) => right.id.localeCompare(left.id)).slice(0, 5);

  return (
    <section className="stack">
      <div className="metric-grid">
        <Metric label="总瓶数" value={summary?.total_bottles ?? 0} />
        <Metric label="在库" value={summary?.in_stock_bottles ?? 0} />
        <Metric label="已出库/损耗" value={summary?.consumed_or_removed_bottles ?? 0} />
        <Metric label="位置数" value={summary?.location_count ?? 0} />
      </div>
      <div className="two-column">
        <section className="panel">
          <h2>最近 Transaction</h2>
          <TransactionTable transactions={summary?.recent_transactions ?? []} compact />
        </section>
        <section className="panel">
          <h2>适饮期提醒</h2>
          <SummaryList
            data={summary?.drink_window_counts ?? {}}
            labels={drinkWindowLabel}
            empty="还没有可统计的在库酒。"
          />
        </section>
      </div>
      <div className="three-column">
        <section className="panel">
          <h2>状态分布</h2>
          <SummaryList data={summary?.status_counts ?? {}} labels={statusLabel} empty="暂无库存状态。" />
        </section>
        <section className="panel">
          <h2>国家 / 产区</h2>
          <SummaryList data={summary?.inventory_by_country ?? {}} empty="暂无国家字段。" />
        </section>
        <section className="panel">
          <h2>酒款类型</h2>
          <SummaryList data={summary?.inventory_by_type ?? {}} empty="暂无类型字段。" />
        </section>
      </div>
      <div className="two-column">
        <section className="panel">
          <h2>酒柜占用</h2>
          {summary?.cellar_occupancy?.length ? (
            <div className="occupancy-list">
              {summary.cellar_occupancy.map((cellar) => (
                <div key={cellar.cellar_id} className="occupancy-row">
                  <div>
                    <strong>{cellar.name}</strong>
                    <span>{cellar.occupied}/{cellar.capacity} 已占用，{cellar.empty} 空位</span>
                  </div>
                  <progress max={Math.max(cellar.capacity, 1)} value={cellar.occupied} />
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">还没有酒柜或位置。</div>
          )}
        </section>
        <section className="panel">
          <h2>最新藏酒</h2>
          <div className="compact-list">
            {latestBottles.map((bottle) => (
              <button key={bottle.id} onClick={() => openBottle(bottle.id)}>
                <span>{bottleTitle(bottle)}</span>
                <small>{formatLocation(bottle)}</small>
              </button>
            ))}
            {!latestBottles.length && <div className="empty">还没有入库记录。</div>}
          </div>
        </section>
      </div>
    </section>
  );
}
