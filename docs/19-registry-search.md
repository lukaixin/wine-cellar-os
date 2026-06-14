# Registry Search & Discovery

最后更新：2026-06-13

本文记录 Beta-2 Registry Search & Discovery 的实现边界。系统继续使用 `Producer -> Wine -> Vintage` 三层 registry，不新增外部 catalog，不接外部数据源，不执行 merge/approve/reject。

## 目标

让已有 registry 可查询、可发现、可验证：

- Producer Search
- Wine Search
- Vintage Search
- Registry detail
- 最近新增 registry entity
- alias conflict / duplicate candidate 风险发现

搜索结果只用于发现和人工核验，不代表权威酒款数据库，也不会自动修改库存。

## Search Service

统一入口：

```text
RegistryService.search(query)
```

返回：

```text
query
producers[]
wines[]
vintages[]
```

每条结果包含：

```text
id
entity_type
display_name
matched_text
matched_by
score
quality_status
```

`matched_by` 当前包括：

```text
canonical_name
alias
fuzzy
chinese_name
partial
```

## 匹配范围

Producer：

- `name_original`
- `name_cn`
- `canonical_key`
- `registry_aliases`
- 旧 `aliases` 字段

Wine：

- `name_original`
- `name_cn`
- `wine_identity_key`
- producer name
- `registry_aliases`
- 旧 `aliases` 字段

Vintage：

- producer + wine + vintage display name
- wine name / wine Chinese name
- producer name / producer Chinese name
- vintage year / NV
- vintage registry alias
- wine registry alias
- producer registry alias

Vintage 继承 Wine/Producer 的 registry alias 只用于搜索发现，不改变数据关系。

## Ranking

排序原则：

```text
canonical exact
> approved alias exact
> fuzzy match
> partial match
```

质量状态会调整分数：

```text
approved/reviewed 提升
unreviewed 保持
needs_review/conflict/rejected 降权
```

内部排序保留匹配优先级，因此 canonical exact 不会因为 alias quality 加分而排到 approved alias 后面。

短查询会避免低置信 fuzzy 扩散；例如 `drc` 主要依赖 canonical exact、alias exact 或 partial，而不是泛化到大量相似字符串。

## API

新增只读接口：

```text
GET /registry/search?q=
GET /registry/discovery
GET /registry/producers/{id}
GET /registry/wines/{id}
GET /registry/vintages/{id}
```

同时提供等价路径：

```text
GET /api/registry/search?q=
GET /api/registry/discovery
GET /api/registry/producers/{id}
GET /api/registry/wines/{id}
GET /api/registry/vintages/{id}
```

示例查询：

```text
/registry/search?q=rayas
/registry/search?q=drc
/registry/search?q=romanee
/registry/search?q=罗曼尼康帝
/registry/search?q=valentini
```

## Detail

Producer Detail：

- canonical name
- Chinese name
- aliases
- country
- region
- wine count
- quality status
- canonical key

Wine Detail：

- canonical name
- Chinese name
- producer
- aliases
- vintage count
- quality status
- wine identity key

Vintage Detail：

- producer
- wine
- vintage / NV
- bottle count
- default drink window
- additional drink window records
- quality status

`bottle_count` 是只读聚合，不修改 Bottle 或 InventoryTransaction。

## Discovery

`GET /registry/discovery` 返回：

- recent producers
- recent wines
- recent vintages
- quality risks

当前 recent entity 按本地 `created_at` 排序，不区分手工创建和导入创建。

质量风险来自 `registry_quality_findings`，当前只展示：

- `alias_conflict`
- `duplicate_producer`
- `duplicate_wine`

Quality findings 仍由本地规则生成，不执行自动合并。

## Frontend

新增 `Registry Search` 页面：

- 搜索框
- Producer / Wine / Vintage 分类结果
- 显示名称、类型、匹配文本、匹配方式、分数、质量状态
- 点击结果加载 detail panel
- 显示 Discovery：recent new registry entity 和质量风险

原 `Registry Quality` 页面继续保留，用于查看 findings、review queue、alias 和 import mapping 明细。

## 非目标

本轮不实现：

- Merge Workflow
- Approve/Reject Workflow
- Recommendation
- AI Sommelier
- External Data Source
- Vivino / CellarTracker 接入
- Price Import
- Auto Merge
- Bottle/Ledger/Inventory 写路径变更

## 验证

后端新增覆盖：

- search service
- alias search
- ranking
- search api
- detail api
- discovery api

前端新增覆盖：

- Registry Search 页面
- 搜索结果分类展示
- detail panel
- discovery 风险展示

最终回归命令：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python -m pytest -q

cd D:\MyLife\17_葡萄酒管理系统\apps\web
npm run build
npm run test:ui
npm run qa:alpha
```

## 已知限制

- Fuzzy 搜索是本地字符串相似度，不是语义搜索。
- Search 不会连接外部酒款数据库。
- Search 命中不等于 registry merge 或 alias approval。
- Discovery recent entity 当前只按 `created_at` 排序。
- Alias provenance 目前在结果里体现为 `matched_text/matched_by`，后续可展示 source/status/reviewed_at。
