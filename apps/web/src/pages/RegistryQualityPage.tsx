import { useEffect, useState } from "react";
import { api } from "../api";
import { DataTable } from "../components/ui/DataTable";
import { Metric } from "../components/ui/Summary";
import type { RegistryQualityData } from "../types";

const emptyRegistryData: RegistryQualityData = {
  aliases: [],
  importMappings: [],
  reviewQueue: [],
  findings: [],
};

export function RegistryQualityPage() {
  const [data, setData] = useState<RegistryQualityData>(emptyRegistryData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void refreshRegistryQuality();
  }, []);

  async function refreshRegistryQuality() {
    setLoading(true);
    setError(null);
    try {
      const [findings, reviewQueue, aliases, importMappings] = await Promise.all([
        api.registryQualityFindings(),
        api.registryReviewQueue(),
        api.registryAliases(),
        api.registryImportMappings(),
      ]);
      setData({ findings, reviewQueue, aliases, importMappings });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registry quality 加载失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="stack">
      <div className="section-heading">
        <div>
          <h2>Registry Quality</h2>
          <span className="subtle">Producer → Wine → Vintage 主数据治理观测</span>
        </div>
        <button className="secondary" type="button" onClick={refreshRegistryQuality} disabled={loading}>
          {loading ? "刷新中" : "刷新"}
        </button>
      </div>

      {error && <div className="banner error">{error}</div>}

      <div className="metric-grid">
        <Metric label="Findings" value={data.findings.length} />
        <Metric label="Review Queue" value={data.reviewQueue.length} />
        <Metric label="Aliases" value={data.aliases.length} />
        <Metric label="Import Mappings" value={data.importMappings.length} />
      </div>

      <section className="panel stack">
        <h2>Findings</h2>
        <DataTable
          className="registry-table"
          headers={["类型", "严重度", "对象", "Evidence", "建议动作", "状态"]}
          empty="当前没有 registry quality finding。"
          rows={data.findings.map((finding) => ({
            key: finding.id,
            cells: [
              finding.finding_type,
              finding.severity,
              formatEntity(finding.entity_type, finding.entity_id),
              <code className="raw-json">{JSON.stringify(finding.evidence)}</code>,
              finding.suggested_action,
              finding.status,
            ],
          }))}
        />
      </section>

      <section className="panel stack">
        <h2>Review Queue</h2>
        <DataTable
          className="registry-table"
          headers={["类型", "标题", "分数", "来源", "对象", "详情", "状态"]}
          empty="当前没有 registry review queue item。"
          rows={data.reviewQueue.map((item) => ({
            key: item.id,
            cells: [
              item.review_type,
              item.title,
              item.match_score ?? "-",
              item.source ?? "-",
              formatEntity(item.entity_type, item.entity_id),
              item.detail ?? "-",
              item.status,
            ],
          }))}
        />
      </section>

      <section className="panel stack">
        <h2>Alias</h2>
        <DataTable
          className="registry-table"
          headers={["对象", "Alias", "Alias Key", "状态", "来源", "规则版本"]}
          empty="当前没有 registry alias。"
          rows={data.aliases.map((alias) => ({
            key: alias.id,
            cells: [
              formatEntity(alias.entity_type, alias.entity_id),
              alias.alias_text,
              alias.alias_key,
              alias.status,
              alias.source ?? "-",
              alias.rule_version,
            ],
          }))}
        />
      </section>

      <section className="panel stack">
        <h2>Import Mapping</h2>
        <DataTable
          className="registry-table"
          headers={["来源", "行", "Raw", "目标", "分数", "Decision", "Evidence"]}
          empty="当前没有 import mapping。"
          rows={data.importMappings.map((mapping) => ({
            key: mapping.id,
            cells: [
              mapping.source,
              mapping.source_row_number ?? "-",
              <code className="raw-json">{JSON.stringify(mapping.raw_value)}</code>,
              formatEntity(mapping.target_entity_type, mapping.target_entity_id),
              mapping.match_score,
              mapping.decision,
              <code className="raw-json">{JSON.stringify(mapping.evidence)}</code>,
            ],
          }))}
        />
      </section>
    </section>
  );
}

function formatEntity(entityType?: string | null, entityId?: string | null): string {
  if (!entityType && !entityId) return "-";
  return [entityType, entityId].filter(Boolean).join(" / ");
}
