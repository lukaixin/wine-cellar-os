import { useEffect, useState } from "react";
import { api } from "../api";
import { statusLabel, transactionLabel } from "../domain/constants";
import type { AnalyticsActivityItem, AnalyticsDistributionItem, AnalyticsSummary } from "../types";
import { Metric } from "../components/ui/Summary";

const eventLabel: Record<AnalyticsActivityItem["event_type"], string> = {
  IMPORT: "入库",
  CONSUME: transactionLabel.CONSUME,
  GIFT: transactionLabel.GIFT,
  MOVE: transactionLabel.MOVE,
  DAMAGE: transactionLabel.DAMAGE,
};

export function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .analytics()
      .then((result) => {
        if (active) {
          setAnalytics(result);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) return <div className="empty">加载中</div>;
  if (error) return <div className="banner error">{error}</div>;
  if (!analytics) return <div className="empty">暂无 Analytics 数据。</div>;

  return (
    <section className="stack">
      <div className="metric-grid">
        <Metric label="Total Bottles" value={analytics.inventory.total_bottles} />
        <Metric label="Total Wines" value={analytics.inventory.total_wines} />
        <Metric label="Total Producers" value={analytics.inventory.total_producers} />
        <Metric label="Total WS Value" value={formatMoney(analytics.inventory.total_ws_value)} />
      </div>

      <div className="three-column">
        <DistributionPanel title="Country Distribution" items={analytics.inventory.country_distribution} />
        <DistributionPanel title="Region Distribution" items={analytics.inventory.region_distribution} />
        <DistributionPanel title="Vintage Distribution" items={analytics.inventory.vintage_distribution} />
      </div>

      <div className="two-column">
        <section className="panel">
          <h2>Status Distribution</h2>
          <DistributionList items={analytics.inventory.status_distribution} labels={statusLabel} />
        </section>
        <section className="panel">
          <h2>Consumption</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Window</th>
                  <th>Consumed</th>
                  <th>Gifted</th>
                  <th>Damaged</th>
                </tr>
              </thead>
              <tbody>
                {analytics.consumption.periods.map((period) => (
                  <tr key={period.key}>
                    <td>{period.label}</td>
                    <td>{period.consumed_bottles}</td>
                    <td>{period.gifted_bottles}</td>
                    <td>{period.damaged_bottles}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <div className="two-column">
        <section className="panel">
          <h2>Monthly Trend</h2>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>Consumed</th>
                  <th>Gifted</th>
                  <th>Damaged</th>
                </tr>
              </thead>
              <tbody>
                {analytics.consumption.monthly_trend.map((row) => (
                  <tr key={row.month}>
                    <td>{row.month}</td>
                    <td>{row.consumed_bottles}</td>
                    <td>{row.gifted_bottles}</td>
                    <td>{row.damaged_bottles}</td>
                  </tr>
                ))}
                {!analytics.consumption.monthly_trend.length && (
                  <tr>
                    <td colSpan={4}>暂无出库事件。</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
        <section className="panel">
          <h2>WS Price Coverage</h2>
          <div className="detail-grid collection-detail-grid">
            <div className="info-item">
              <span>Priced Bottles</span>
              <strong>{analytics.inventory.ws_priced_bottles}</strong>
            </div>
            <div className="info-item">
              <span>Total WS Value</span>
              <strong>{formatMoney(analytics.inventory.total_ws_value)}</strong>
            </div>
          </div>
        </section>
      </div>

      <section className="panel">
        <h2>Recent Activity</h2>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Event</th>
                <th>Bottle</th>
                <th>Time</th>
                <th>From</th>
                <th>To</th>
                <th>Note</th>
              </tr>
            </thead>
            <tbody>
              {analytics.activity.map((item) => (
                <tr key={item.transaction_id}>
                  <td>{eventLabel[item.event_type]}</td>
                  <td>{item.bottle_label ?? item.bottle_id}</td>
                  <td>{new Date(item.occurred_at).toLocaleString("zh-CN")}</td>
                  <td>{formatLocation(item.from_location)}</td>
                  <td>{formatLocation(item.to_location)}</td>
                  <td>{[item.reason, item.note].filter(Boolean).join(" · ") || "-"}</td>
                </tr>
              ))}
              {!analytics.activity.length && (
                <tr>
                  <td colSpan={6}>暂无库存活动。</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </section>
  );
}

function DistributionPanel({ title, items }: { title: string; items: AnalyticsDistributionItem[] }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <DistributionList items={items} />
    </section>
  );
}

function DistributionList({
  items,
  labels = {},
}: {
  items: AnalyticsDistributionItem[];
  labels?: Record<string, string>;
}) {
  return (
    <div className="status-list">
      {items.map((item) => (
        <div key={item.label} className="status-row">
          <span>{labels[item.label] ?? item.label}</span>
          <strong>{item.count}</strong>
        </div>
      ))}
      {!items.length && <div className="empty compact-empty">暂无数据。</div>}
    </div>
  );
}

function formatMoney(value?: string | null) {
  if (!value) return "-";
  return `¥${Number(value).toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatLocation(location: { cellar_name?: string | null; code?: string | null }) {
  return [location.cellar_name, location.code].filter(Boolean).join(" / ") || "-";
}
