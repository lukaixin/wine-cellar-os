import { FormEvent, useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { DataTable } from "../components/ui/DataTable";
import { InfoItem } from "../components/ui/InfoItem";
import { Metric } from "../components/ui/Summary";
import type {
  RegistryDetail,
  RegistryDiscovery,
  RegistryDiscoveryItem,
  RegistryEntityType,
  RegistryQualityRisk,
  RegistrySearchResponse,
  RegistrySearchResult,
} from "../types";

const emptySearch: RegistrySearchResponse = {
  query: "",
  producers: [],
  wines: [],
  vintages: [],
};

const emptyDiscovery: RegistryDiscovery = {
  recent_producers: [],
  recent_wines: [],
  recent_vintages: [],
  quality_risks: [],
};

export function RegistrySearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<RegistrySearchResponse>(emptySearch);
  const [discovery, setDiscovery] = useState<RegistryDiscovery>(emptyDiscovery);
  const [detail, setDetail] = useState<RegistryDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshDiscovery();
  }, []);

  const totalResults = useMemo(
    () => results.producers.length + results.wines.length + results.vintages.length,
    [results],
  );

  async function refreshDiscovery() {
    try {
      setDiscovery(await api.registryDiscovery());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registry discovery 加载失败");
    }
  }

  async function submitSearch(event: FormEvent) {
    event.preventDefault();
    const nextQuery = query.trim();
    setError(null);
    setDetail(null);
    if (!nextQuery) {
      setResults(emptySearch);
      return;
    }
    setLoading(true);
    try {
      setResults(await api.registrySearch(nextQuery));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registry search 失败");
    } finally {
      setLoading(false);
    }
  }

  async function openDetail(entityType: RegistryEntityType, id: string) {
    setDetailLoading(true);
    setError(null);
    try {
      setDetail(await api.registryDetail(entityType, id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registry detail 加载失败");
    } finally {
      setDetailLoading(false);
    }
  }

  return (
    <section className="stack">
      <form className="panel search-panel" onSubmit={submitSearch}>
        <label>
          <span>Registry 查询</span>
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="rayas / drc / romanee / 罗曼尼康帝 / valentini"
          />
        </label>
        <button type="submit" disabled={loading}>{loading ? "搜索中" : "搜索"}</button>
      </form>

      {error && <div className="banner error">{error}</div>}

      <div className="metric-grid">
        <Metric label="Producer Results" value={results.producers.length} />
        <Metric label="Wine Results" value={results.wines.length} />
        <Metric label="Vintage Results" value={results.vintages.length} />
        <Metric label="Quality Risks" value={discovery.quality_risks.length} />
      </div>

      <div className="two-column registry-search-layout">
        <section className="stack">
          {results.query ? (
            <div className="section-heading">
              <div>
                <h2>Search Results</h2>
                <span className="subtle">{results.query} · {totalResults} 条结果</span>
              </div>
            </div>
          ) : null}

          <RegistryResultTable title="Producer" rows={results.producers} openDetail={openDetail} />
          <RegistryResultTable title="Wine" rows={results.wines} openDetail={openDetail} />
          <RegistryResultTable title="Vintage" rows={results.vintages} openDetail={openDetail} />
        </section>

        <section className="stack">
          <RegistryDetailPanel detail={detail} loading={detailLoading} />
          <DiscoveryPanel discovery={discovery} openDetail={openDetail} />
        </section>
      </div>
    </section>
  );
}

function RegistryResultTable({
  title,
  rows,
  openDetail,
}: {
  title: string;
  rows: RegistrySearchResult[];
  openDetail: (entityType: RegistryEntityType, id: string) => void;
}) {
  return (
    <section className="panel stack">
      <h2>{title}</h2>
      <DataTable
        className="registry-table"
        headers={["名称", "类型", "匹配文本", "匹配方式", "分数", "质量"]}
        empty={`没有 ${title} 结果。`}
        rows={rows.map((item) => ({
          key: item.id,
          onClick: () => openDetail(item.entity_type, item.id),
          cells: [
            item.display_name,
            entityTypeLabel(item.entity_type),
            item.matched_text,
            matchedByLabel(item.matched_by),
            item.score,
            <QualityBadge status={item.quality_status} />,
          ],
        }))}
      />
    </section>
  );
}

function RegistryDetailPanel({ detail, loading }: { detail: RegistryDetail | null; loading: boolean }) {
  if (loading) return <section className="panel empty">详情加载中</section>;
  if (!detail) return <section className="panel empty">选择一条搜索结果查看详情。</section>;
  if (detail.entity_type === "producer") {
    return (
      <section className="panel stack">
        <DetailHeading title={detail.canonical_name} type="Producer" status={detail.quality_status} />
        <div className="detail-grid">
          <InfoItem label="中文名" value={detail.name_cn ?? "-"} />
          <InfoItem label="国家" value={detail.country ?? "-"} />
          <InfoItem label="产区" value={detail.region ?? "-"} />
          <InfoItem label="Wine Count" value={detail.wine_count} />
        </div>
        <AliasList aliases={detail.aliases} />
      </section>
    );
  }
  if (detail.entity_type === "wine") {
    return (
      <section className="panel stack">
        <DetailHeading title={detail.canonical_name} type="Wine" status={detail.quality_status} />
        <div className="detail-grid">
          <InfoItem label="Producer" value={detail.producer_name} />
          <InfoItem label="中文名" value={detail.name_cn ?? "-"} />
          <InfoItem label="Vintage Count" value={detail.vintage_count} />
          <InfoItem label="Identity Key" value={<code className="raw-json">{detail.wine_identity_key ?? "-"}</code>} />
        </div>
        <AliasList aliases={detail.aliases} />
      </section>
    );
  }
  return (
    <section className="panel stack">
      <DetailHeading
        title={`${detail.producer_name} · ${detail.wine_name} · ${detail.is_non_vintage ? "NV" : detail.vintage_year ?? "未知年份"}`}
        type="Vintage"
        status={detail.quality_status}
      />
      <div className="detail-grid">
        <InfoItem label="Producer" value={detail.producer_name} />
        <InfoItem label="Wine" value={detail.wine_name} />
        <InfoItem label="Bottle Count" value={detail.bottle_count} />
        <InfoItem label="默认适饮期" value={formatDrinkWindow(detail.default_drink_from, detail.default_drink_to)} />
      </div>
      <DataTable
        className="registry-table"
        headers={["来源", "适饮期", "Peak", "置信度", "备注"]}
        empty="没有额外 drink window。"
        rows={detail.drink_windows.map((window, index) => ({
          key: `${window.source}-${index}`,
          cells: [
            window.source,
            formatDrinkWindow(window.drink_from, window.drink_to),
            formatDrinkWindow(window.peak_from, window.peak_to),
            window.confidence,
            window.notes ?? window.source_detail ?? "-",
          ],
        }))}
      />
    </section>
  );
}

function DiscoveryPanel({
  discovery,
  openDetail,
}: {
  discovery: RegistryDiscovery;
  openDetail: (entityType: RegistryEntityType, id: string) => void;
}) {
  return (
    <section className="panel stack">
      <h2>Discovery</h2>
      <div className="three-column discovery-list">
        <DiscoveryList title="New Producers" items={discovery.recent_producers} openDetail={openDetail} />
        <DiscoveryList title="New Wines" items={discovery.recent_wines} openDetail={openDetail} />
        <DiscoveryList title="New Vintages" items={discovery.recent_vintages} openDetail={openDetail} />
      </div>
      <DataTable
        className="registry-table"
        headers={["风险", "严重度", "对象", "建议"]}
        empty="当前没有 alias conflict 或 duplicate candidate。"
        rows={discovery.quality_risks.map((risk) => ({
          key: risk.id,
          onClick: risk.entity_type && risk.entity_id ? () => openDetail(risk.entity_type as RegistryEntityType, risk.entity_id as string) : undefined,
          cells: [
            risk.finding_type,
            risk.severity,
            formatEntity(risk.entity_type, risk.entity_id),
            risk.suggested_action,
          ],
        }))}
      />
    </section>
  );
}

function DiscoveryList({
  title,
  items,
  openDetail,
}: {
  title: string;
  items: RegistryDiscoveryItem[];
  openDetail: (entityType: RegistryEntityType, id: string) => void;
}) {
  return (
    <div className="mini-form discovery-card">
      <h3>{title}</h3>
      {items.length ? (
        items.map((item) => (
          <button className="compact-button secondary" type="button" key={item.id} onClick={() => openDetail(item.entity_type, item.id)}>
            {item.display_name}
          </button>
        ))
      ) : (
        <span className="subtle">-</span>
      )}
    </div>
  );
}

function DetailHeading({ title, type, status }: { title: string; type: string; status: string }) {
  return (
    <div className="detail-header">
      <div>
        <h2>{title}</h2>
        <p>{type}</p>
      </div>
      <QualityBadge status={status} />
    </div>
  );
}

function AliasList({ aliases }: { aliases: string[] }) {
  return (
    <div className="alias-list">
      <span className="subtle">Alias</span>
      {aliases.length ? aliases.map((alias) => <span className="status-pill" key={alias}>{alias}</span>) : <span>-</span>}
    </div>
  );
}

function QualityBadge({ status }: { status: string }) {
  return <span className={`quality-badge ${status}`}>{status}</span>;
}

function entityTypeLabel(type: RegistryEntityType): string {
  return { producer: "Producer", wine: "Wine", vintage: "Vintage" }[type];
}

function matchedByLabel(value: string): string {
  return {
    canonical_name: "Canonical",
    alias: "Alias",
    fuzzy: "Fuzzy",
    chinese_name: "中文名",
    partial: "Partial",
  }[value] ?? value;
}

function formatDrinkWindow(from?: number | null, to?: number | null): string {
  if (!from && !to) return "-";
  return `${from ?? "?"}-${to ?? "?"}`;
}

function formatEntity(entityType?: string | null, entityId?: string | null): string {
  if (!entityType && !entityId) return "-";
  return [entityType, entityId].filter(Boolean).join(" / ");
}
