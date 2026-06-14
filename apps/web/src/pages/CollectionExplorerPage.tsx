import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { InfoItem } from "../components/ui/InfoItem";
import { statusLabel, transactionLabel } from "../domain/constants";
import type {
  AppData,
  CollectionBottleDetail,
  CollectionBottleTimelineEvent,
  CollectionSearchItem,
  CollectionSearchResponse,
  Location,
} from "../types";

const emptyResults: CollectionSearchResponse = {
  query: null,
  total: 0,
  limit: 25,
  offset: 0,
  items: [],
};

const pageSize = 25;

export function CollectionExplorerPage({
  data,
  afterMutation,
}: {
  data: AppData;
  afterMutation: (message: string) => Promise<void>;
}) {
  const [query, setQuery] = useState("");
  const [producerId, setProducerId] = useState("");
  const [vintageYear, setVintageYear] = useState("");
  const [locationId, setLocationId] = useState("");
  const [status, setStatus] = useState("");
  const [offset, setOffset] = useState(0);
  const [results, setResults] = useState<CollectionSearchResponse>(emptyResults);
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [detail, setDetail] = useState<CollectionBottleDetail | null>(null);
  const [timeline, setTimeline] = useState<CollectionBottleTimelineEvent[]>([]);
  const [activeTab, setActiveTab] = useState<"detail" | "timeline" | "actions">("detail");
  const [actionNotice, setActionNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const vintageYears = useMemo(
    () => Array.from(new Set(data.vintages.map((item) => item.vintage_year).filter((year): year is number => typeof year === "number"))).sort((a, b) => b - a),
    [data.vintages],
  );
  const statuses = useMemo(
    () => Array.from(new Set(data.bottles.map((bottle) => bottle.current_status))).sort(),
    [data.bottles],
  );

  useEffect(() => {
    void runSearch(0);
  }, []);

  async function runSearch(nextOffset = offset, clearMissingDetail = true) {
    const params = new URLSearchParams();
    const trimmedQuery = query.trim();
    if (trimmedQuery) params.set("q", trimmedQuery);
    if (producerId) params.set("producer_id", producerId);
    if (vintageYear) params.set("vintage_year", vintageYear);
    if (locationId) params.set("location_id", locationId);
    if (status) params.set("status", status);
    params.set("limit", String(pageSize));
    params.set("offset", String(nextOffset));
    setLoading(true);
    setError(null);
    try {
      const response = await api.collectionSearch(params);
      setResults(response);
      setOffset(nextOffset);
      if (clearMissingDetail && !response.items.some((item) => item.bottle_ids.includes(detail?.id ?? ""))) {
        setDetail(null);
        setTimeline([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Collection search 失败");
    } finally {
      setLoading(false);
    }
  }

  function submitSearch(event: FormEvent) {
    event.preventDefault();
    void runSearch(0);
  }

  async function openBottleDetail(bottleId: string) {
    setDetailLoading(true);
    setError(null);
    try {
      await refreshBottleDetail(bottleId);
      setActiveTab("detail");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bottle detail 加载失败");
    } finally {
      setDetailLoading(false);
    }
  }

  async function refreshBottleDetail(bottleId: string) {
    const [nextDetail, nextTimeline] = await Promise.all([
      api.collectionBottle(bottleId),
      api.collectionBottleTimeline(bottleId),
    ]);
    setDetail(nextDetail);
    setTimeline(nextTimeline);
  }

  async function handleActionComplete(bottleId: string, message: string) {
    setActionNotice(message);
    await refreshBottleDetail(bottleId);
    await runSearch(offset, false);
    await afterMutation(message);
    setActiveTab("timeline");
  }

  function toggleGroup(item: CollectionSearchItem) {
    const key = groupKey(item);
    setExpandedGroups((current) => {
      const next = new Set(current);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  return (
    <section className="collection-explorer">
      <aside className="panel collection-filters">
        <h2>Filters</h2>
        <label>
          <span>Producer</span>
          <select value={producerId} onChange={(event) => setProducerId(event.target.value)}>
            <option value="">All producers</option>
            {data.producers.map((producer) => (
              <option key={producer.id} value={producer.id}>{producer.name_cn || producer.name_original}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Vintage</span>
          <select value={vintageYear} onChange={(event) => setVintageYear(event.target.value)}>
            <option value="">All vintages</option>
            {vintageYears.map((year) => <option key={year} value={year}>{year}</option>)}
          </select>
        </label>
        <label>
          <span>Location</span>
          <select value={locationId} onChange={(event) => setLocationId(event.target.value)}>
            <option value="">All locations</option>
            {data.locations.map((location) => (
              <option key={location.id} value={location.id}>{formatLocationName(location.cellar_name, location.code)}</option>
            ))}
          </select>
        </label>
        <label>
          <span>Status</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            {statuses.map((item) => <option key={item} value={item}>{statusLabel[item] ?? item}</option>)}
          </select>
        </label>
        <button type="button" onClick={() => void runSearch(0)} disabled={loading}>{loading ? "筛选中" : "应用筛选"}</button>
      </aside>

      <section className="stack collection-main">
        <form className="panel search-panel" onSubmit={submitSearch}>
          <label>
            <span>Collection Search</span>
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Rayas / 2016 Rayas / DRC / 罗曼尼康帝"
            />
          </label>
          <button type="submit" disabled={loading}>{loading ? "搜索中" : "搜索"}</button>
        </form>

        {error && <div className="banner error">{error}</div>}

        <section className="panel stack">
          <div className="section-heading">
            <div>
              <h2>Result List</h2>
              <span className="subtle">{results.total} groups · page {Math.floor(offset / pageSize) + 1}</span>
            </div>
            <div className="pagination-actions">
              <button type="button" className="secondary" disabled={offset <= 0 || loading} onClick={() => void runSearch(Math.max(0, offset - pageSize))}>
                上一页
              </button>
              <button type="button" className="secondary" disabled={offset + pageSize >= results.total || loading} onClick={() => void runSearch(offset + pageSize)}>
                下一页
              </button>
            </div>
          </div>
          <CollectionResultsTable
            items={results.items}
            expandedGroups={expandedGroups}
            selectedBottleId={detail?.id ?? null}
            onToggleGroup={toggleGroup}
            onSelectBottle={openBottleDetail}
          />
        </section>
      </section>

      <CollectionBottleDrawer
        activeTab={activeTab}
        detail={detail}
        loading={detailLoading}
        locations={data.locations}
        notice={actionNotice}
        onActionComplete={handleActionComplete}
        onTabChange={setActiveTab}
        timeline={timeline}
      />
    </section>
  );
}

function CollectionResultsTable({
  items,
  expandedGroups,
  selectedBottleId,
  onToggleGroup,
  onSelectBottle,
}: {
  items: CollectionSearchItem[];
  expandedGroups: Set<string>;
  selectedBottleId: string | null;
  onToggleGroup: (item: CollectionSearchItem) => void;
  onSelectBottle: (bottleId: string) => void;
}) {
  if (!items.length) return <div className="empty">没有找到匹配的库存酒瓶。</div>;
  return (
    <div className="table-wrap">
      <table className="collection-table">
        <thead>
          <tr>
            <th>Producer</th>
            <th>Wine</th>
            <th>Vintage</th>
            <th>Bottles</th>
            <th>Location</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {items.flatMap((item) => {
            const key = groupKey(item);
            const isExpanded = expandedGroups.has(key);
            const rows = [
              <tr key={key}>
                <td>{displayName(item.producer_name_cn, item.producer_name)}</td>
                <td>{displayName(item.wine_name_cn, item.wine_name)}</td>
                <td>{formatVintage(item)}</td>
                <td>
                  <button type="button" className="secondary group-toggle" onClick={() => onToggleGroup(item)}>
                    {isExpanded ? "收起" : "展开"} {item.bottle_count} Bottles
                  </button>
                </td>
                <td>{formatLocationName(item.location.cellar_name, item.location.code)}</td>
                <td>{statusLabel[item.status] ?? item.status}</td>
              </tr>,
            ];
            if (isExpanded) {
              rows.push(
                <tr key={`${key}-bottles`} className="bottle-list-row">
                  <td colSpan={6}>
                    <div className="bottle-list">
                      {item.bottle_ids.map((bottleId, index) => (
                        <button
                          key={bottleId}
                          type="button"
                          className={bottleId === selectedBottleId ? "active-bottle" : "secondary"}
                          onClick={() => onSelectBottle(bottleId)}
                        >
                          Bottle #{index + 1} · {shortBottleId(bottleId)}
                        </button>
                      ))}
                    </div>
                  </td>
                </tr>,
              );
            }
            return rows;
          })}
        </tbody>
      </table>
    </div>
  );
}

function CollectionBottleDrawer({
  activeTab,
  detail,
  loading,
  locations,
  notice,
  onActionComplete,
  onTabChange,
  timeline,
}: {
  activeTab: "detail" | "timeline" | "actions";
  detail: CollectionBottleDetail | null;
  loading: boolean;
  locations: Location[];
  notice: string | null;
  onActionComplete: (bottleId: string, message: string) => Promise<void>;
  onTabChange: (tab: "detail" | "timeline" | "actions") => void;
  timeline: CollectionBottleTimelineEvent[];
}) {
  if (loading) return <aside className="panel collection-detail-drawer empty">Bottle detail 加载中</aside>;
  if (!detail) return <aside className="panel collection-detail-drawer empty">选择一行查看 Bottle Detail。</aside>;
  return (
    <aside className="panel collection-detail-drawer stack">
      <div className="detail-header">
        <div>
          <h2>{displayName(detail.wine_name_cn, detail.wine_name)}</h2>
          <p>{displayName(detail.producer_name_cn, detail.producer_name)} · {formatVintage(detail)}</p>
        </div>
        <span className="status-pill">{statusLabel[detail.status] ?? detail.status}</span>
      </div>
      <div className="drawer-tabs" role="tablist" aria-label="Bottle detail sections">
        <button type="button" className={activeTab === "detail" ? "active" : "secondary"} onClick={() => onTabChange("detail")}>
          Detail
        </button>
        <button type="button" className={activeTab === "timeline" ? "active" : "secondary"} onClick={() => onTabChange("timeline")}>
          Timeline
        </button>
        <button type="button" className={activeTab === "actions" ? "active" : "secondary"} onClick={() => onTabChange("actions")}>
          Actions
        </button>
      </div>
      {activeTab === "detail" ? (
        <div className="detail-grid collection-detail-grid">
          <InfoItem label="Bottle" value={detail.bottle_id} />
          <InfoItem label="Quantity" value={detail.quantity} />
          <InfoItem label="Bottle Size" value={`${detail.bottle_size_ml} ml`} />
          <InfoItem label="Location" value={formatLocationName(detail.location.cellar_name, detail.location.code)} />
          <InfoItem label="Acquisition Date" value={detail.acquisition_date ?? "-"} />
          <InfoItem label="Vintage" value={formatVintage(detail)} />
          <InfoItem label="Producer" value={displayName(detail.producer_name_cn, detail.producer_name)} />
          <InfoItem label="Wine" value={displayName(detail.wine_name_cn, detail.wine_name)} />
          <InfoItem label="Producer ID" value={detail.producer_id ?? "-"} />
          <InfoItem label="Wine ID" value={detail.wine_id ?? "-"} />
          <InfoItem label="Vintage ID" value={detail.vintage_id} />
        </div>
      ) : activeTab === "timeline" ? (
        <CollectionBottleTimeline events={timeline} />
      ) : (
        <CollectionBottleActions
          detail={detail}
          locations={locations}
          notice={notice}
          onActionComplete={onActionComplete}
        />
      )}
    </aside>
  );
}

type InventoryActionKind = "CONSUME" | "GIFT" | "MOVE" | "DAMAGE";

function CollectionBottleActions({
  detail,
  locations,
  notice,
  onActionComplete,
}: {
  detail: CollectionBottleDetail;
  locations: Location[];
  notice: string | null;
  onActionComplete: (bottleId: string, message: string) => Promise<void>;
}) {
  const [action, setAction] = useState<InventoryActionKind>("CONSUME");
  const [quantity, setQuantity] = useState("1");
  const [targetLocationId, setTargetLocationId] = useState("");
  const [recipient, setRecipient] = useState("");
  const [damageReason, setDamageReason] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isInStock = detail.status === "in_stock";
  const availableMoveLocations = locations.filter((location) => location.id !== detail.location.id);

  async function submitAction(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!isInStock) {
      setError("只有在库酒瓶可以执行库存操作。");
      return;
    }
    const parsedQuantity = Number(quantity);
    if (!Number.isInteger(parsedQuantity) || parsedQuantity !== 1) {
      setError("单瓶操作数量必须为 1。");
      return;
    }
    if (action === "MOVE" && (!detail.location.id || !targetLocationId)) {
      setError("移动必须选择当前位置和目标位置。");
      return;
    }
    if (action === "GIFT" && !recipient.trim()) {
      setError("送礼必须填写 Recipient。");
      return;
    }
    if (action === "DAMAGE" && !damageReason.trim()) {
      setError("损耗必须填写 Reason。");
      return;
    }

    setSubmitting(true);
    try {
      if (action === "MOVE") {
        await api.moveBottle({
          bottle_id: detail.id,
          from_location: detail.location.id ?? "",
          to_location: targetLocationId,
          notes: notes.trim() || null,
        });
      } else if (action === "GIFT") {
        await api.giftBottle({
          bottle_id: detail.id,
          quantity: parsedQuantity,
          recipient: recipient.trim(),
          notes: notes.trim() || null,
        });
      } else if (action === "DAMAGE") {
        await api.damageBottle({
          bottle_id: detail.id,
          quantity: parsedQuantity,
          reason: damageReason.trim(),
          notes: notes.trim() || null,
        });
      } else {
        await api.consumeBottle({
          bottle_id: detail.id,
          quantity: parsedQuantity,
          notes: notes.trim() || null,
        });
      }
      setNotes("");
      setRecipient("");
      setDamageReason("");
      setTargetLocationId("");
      await onActionComplete(detail.id, `${transactionLabel[action]}已记录`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "库存操作失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form className="collection-actions" onSubmit={submitAction}>
      {notice && <div className="banner success">{notice}</div>}
      {error && <div className="banner error">{error}</div>}
      {!isInStock && <div className="banner warning">当前状态为{statusLabel[detail.status] ?? detail.status}，不能执行出库或移动操作。</div>}
      <div className="action-button-row" role="group" aria-label="Inventory action type">
        {(["CONSUME", "GIFT", "MOVE", "DAMAGE"] as InventoryActionKind[]).map((item) => (
          <button
            key={item}
            type="button"
            className={action === item ? "active" : "secondary"}
            disabled={!isInStock || submitting}
            onClick={() => setAction(item)}
          >
            {transactionLabel[item]}
          </button>
        ))}
      </div>
      {action !== "MOVE" && (
        <label>
          <span>Quantity</span>
          <input value={quantity} onChange={(event) => setQuantity(event.target.value)} inputMode="numeric" disabled={!isInStock || submitting} />
        </label>
      )}
      {action === "MOVE" && (
        <label>
          <span>目标位置</span>
          <select value={targetLocationId} onChange={(event) => setTargetLocationId(event.target.value)} disabled={!isInStock || submitting}>
            <option value="">选择目标位置</option>
            {availableMoveLocations.map((location) => (
              <option key={location.id} value={location.id}>{formatLocationName(location.cellar_name, location.code)}</option>
            ))}
          </select>
        </label>
      )}
      {action === "GIFT" && (
        <label>
          <span>Recipient</span>
          <input value={recipient} onChange={(event) => setRecipient(event.target.value)} disabled={!isInStock || submitting} />
        </label>
      )}
      {action === "DAMAGE" && (
        <label>
          <span>Reason</span>
          <input value={damageReason} onChange={(event) => setDamageReason(event.target.value)} disabled={!isInStock || submitting} />
        </label>
      )}
      <label>
        <span>Notes</span>
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} disabled={!isInStock || submitting} />
      </label>
      <button type="submit" disabled={!isInStock || submitting}>
        {submitting ? "提交中" : `确认${transactionLabel[action]}`}
      </button>
    </form>
  );
}

function CollectionBottleTimeline({ events }: { events: CollectionBottleTimelineEvent[] }) {
  if (!events.length) return <div className="empty">暂无库存事件。</div>;
  return (
    <ol className="timeline collection-timeline">
      {events.map((event) => (
        <li key={event.reference_id}>
          <div className="timeline-dot" />
          <div className="timeline-card">
            <div className="timeline-top">
              <strong>{transactionLabel[event.event_type] ?? event.event_type}</strong>
              <span>{new Date(event.event_time).toLocaleString("zh-CN")}</span>
            </div>
            <div className="subtle">
              {formatTimelineLocation(event)}
              {event.quantity_delta !== 0 ? ` · ${event.quantity_delta > 0 ? "+" : ""}${event.quantity_delta} bottle` : ""}
            </div>
            {event.notes && <p>{event.notes}</p>}
          </div>
        </li>
      ))}
    </ol>
  );
}

function groupKey(item: CollectionSearchItem): string {
  return `${item.vintage_id}-${item.location.id ?? "none"}-${item.status}`;
}

function shortBottleId(bottleId: string): string {
  return bottleId.length > 8 ? bottleId.slice(0, 8) : bottleId;
}

function formatTimelineLocation(event: CollectionBottleTimelineEvent): string {
  const fromLocation = formatLocationName(event.from_location.cellar_name, event.from_location.code);
  const toLocation = formatLocationName(event.to_location.cellar_name, event.to_location.code);
  if (event.from_location.id && event.to_location.id) return `${fromLocation} → ${toLocation}`;
  if (event.to_location.id) return `到 ${toLocation}`;
  if (event.from_location.id) return `从 ${fromLocation}`;
  return "无位置变化";
}

function displayName(primary?: string | null, fallback?: string | null): string {
  return primary || fallback || "-";
}

function formatVintage(item: { is_non_vintage: boolean; vintage_year?: number | null }): string {
  if (item.is_non_vintage) return "NV";
  return item.vintage_year ? String(item.vintage_year) : "-";
}

function formatLocationName(cellarName?: string | null, code?: string | null): string {
  if (!cellarName && !code) return "无位置";
  return [cellarName, code].filter(Boolean).join(" / ");
}
