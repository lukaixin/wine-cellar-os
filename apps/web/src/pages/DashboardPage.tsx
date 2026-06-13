import { drinkWindowStatusLabel, statusLabel } from "../domain/constants";
import type { AppData, DashboardBottleInsight } from "../types";
import { bottleTitle, formatLocation } from "../utils/wine";
import { TransactionTable } from "../components/transactions/TransactionTable";
import { Metric, SummaryList } from "../components/ui/Summary";

export function DashboardPage({ data, openBottle }: { data: AppData; openBottle: (id: string) => void }) {
  const summary = data.dashboard;
  const health = summary?.cellar_health_score;
  const latestBottles = [...data.bottles].sort((left, right) => right.id.localeCompare(left.id)).slice(0, 5);

  return (
    <section className="stack">
      <div className="metric-grid">
        <Metric label="总瓶数" value={summary?.total_bottles ?? 0} />
        <Metric label="在库可用" value={summary?.available_bottles ?? summary?.in_stock_bottles ?? 0} />
        <Metric label="已出库/不可用" value={summary?.unavailable_bottles ?? summary?.consumed_or_removed_bottles ?? 0} />
        <Metric label="酒窖健康" value={health ? `${health.score}` : "-"} />
      </div>

      <div className="two-column">
        <section className="panel health-panel">
          <div className="health-header">
            <div>
              <h2>酒窖健康</h2>
              <p>{health?.label ?? "暂无数据"}</p>
            </div>
            <strong>{health ? `${health.score}/100` : "-"}</strong>
          </div>
          {health ? (
            <div className="health-factor-list">
              {health.factors.map((factor) => (
                <div key={factor.key} className="health-factor">
                  <div>
                    <span>{factor.label}</span>
                    <strong>{factor.score}</strong>
                  </div>
                  <p>{factor.detail}</p>
                  <progress max={100} value={factor.score} />
                </div>
              ))}
              {health.notes.map((note) => (
                <small key={note} className="subtle">{note}</small>
              ))}
            </div>
          ) : (
            <div className="empty compact-empty">还没有可计算的库存健康数据。</div>
          )}
        </section>

        <section className="panel">
          <h2>最近 Transaction</h2>
          <TransactionTable transactions={summary?.recent_transactions ?? []} compact />
        </section>
      </div>

      <div className="three-column">
        <section className="panel">
          <h2>适饮状态</h2>
          <SummaryList data={summary?.drink_window_summary ?? {}} labels={drinkWindowStatusLabel} empty="还没有可统计的在库酒。" />
        </section>
        <section className="panel">
          <h2>库存状态</h2>
          <SummaryList data={summary?.status_counts ?? {}} labels={statusLabel} empty="暂无库存状态。" />
        </section>
        <section className="panel">
          <h2>国家 / 产区</h2>
          <SummaryList data={summary?.inventory_by_country ?? {}} empty="暂无国家字段。" />
        </section>
      </div>

      <div className="two-column">
        <InsightList
          title="近期可喝"
          items={summary?.upcoming_drink_candidates ?? []}
          empty="没有进入或即将进入适饮期的在库酒。"
          openBottle={openBottle}
        />
        <InsightList
          title="过期风险"
          items={summary?.past_window_risks ?? []}
          empty="没有超过建议适饮期的在库酒。"
          openBottle={openBottle}
        />
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

function InsightList({
  title,
  items,
  empty,
  openBottle,
}: {
  title: string;
  items: DashboardBottleInsight[];
  empty: string;
  openBottle: (id: string) => void;
}) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <div className="compact-list insight-list">
        {items.map((item) => (
          <button key={item.bottle_id} className="insight-button" onClick={() => openBottle(item.bottle_id)}>
            <span>{item.bottle_label}</span>
            <small>{[item.cellar_name, item.location_code].filter(Boolean).join(" / ") || "无位置"}</small>
            <small>{formatInsightWindow(item)} · {drinkWindowStatusLabel[item.drink_window_status]}</small>
            <small>{item.reason}</small>
          </button>
        ))}
        {!items.length && <div className="empty compact-empty">{empty}</div>}
      </div>
    </section>
  );
}

function formatInsightWindow(item: DashboardBottleInsight): string {
  if (!item.drink_from || !item.drink_to) return "未设置适饮期";
  return `${item.drink_from}-${item.drink_to}`;
}
