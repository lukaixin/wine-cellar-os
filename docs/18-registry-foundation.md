# Registry Foundation Schema

最后更新：2026-06-13

本文记录 Beta-1A Registry Foundation 的实现边界。系统不新增 `WineRegistry` 根表，继续以 `Producer -> Wine -> Vintage` 作为主数据层，并在其上增加治理字段、alias、导入映射、review queue 和质量发现。

## 设计边界

- 不迁移 `Bottle.vintage_id`，不修改 `InventoryTransaction`。
- 不删除历史 Producer/Wine/Vintage/Bottle/Transaction 数据。
- 不加硬唯一约束；疑似重复只进入 finding/review，不自动合并。
- `alias` 不等于合并。只有 `approved` alias 可以作为稳定匹配依据。
- `merged_into_id` 只是人工治理标记，本轮不实现审批流或合并流程。
- WineList draft 可以记录 registry mapping 和 review queue，但仍不创建正式库存；confirm 才通过 `InventoryService` 写入 Bottle 和 `IN` ledger。

## Schema

### producers

新增字段：

```text
canonical_key text nullable index
quality_status text default 'unreviewed'
merged_into_id uuid/text nullable
reviewed_at datetime nullable
```

`canonical_key` 由 `name_original/name_cn` 标准化生成，用于可观测匹配和重复发现，不是唯一约束。

### wines

新增字段：

```text
wine_identity_key text nullable index
quality_status text default 'unreviewed'
merged_into_id uuid/text nullable
reviewed_at datetime nullable
```

`wine_identity_key` 至少包含 producer key 和 wine name，不允许只由酒名构成；当前还包含 country、region、appellation、type 等已有上下文。

### vintages

新增字段：

```text
quality_status text default 'unreviewed'
reviewed_at datetime nullable
```

### registry_aliases

记录 registry 别名，不直接触发合并。

状态：

```text
observed / candidate / approved / rejected / conflict
```

支持对象：

```text
producer / wine / vintage
```

只有 `approved` 且无冲突的 alias 可以用于稳定匹配。冲突 alias 会进入 `registry_review_queue`。

### import_mappings

记录导入匹配过程：

```text
source
import_batch_id / import_batch_row_id
source_row_number
raw_value
target_entity_type
target_entity_id
match_score
decision
rule_version
evidence
```

Decision：

```text
auto_accepted / needs_review / manual_required / rejected
```

### registry_review_queue

只读观察队列，本轮不实现审批动作。

类型：

```text
match_range        # 80-95 分匹配
alias_conflict
suspected_duplicate
missing_field
```

### registry_quality_findings

记录质量发现：

```text
duplicate_producer
duplicate_wine
alias_conflict
missing_vintage
missing_drink_window
missing_region
missing_country
```

每条 finding 包含：

```text
severity
entity_type / entity_id
evidence
evidence_hash
suggested_action
status
```

## Canonical Key 规则

标准化服务执行：

1. NFKC。
2. trim。
3. casefold。
4. 去重音。
5. 标准化空格。
6. 标准化常见中英文标点、引号、连字符。

示例：

```text
" Château　d’Yquem – Sautérnes " -> "chateau d yquem sauternes"
```

Wine identity 示例：

```text
domaine de la romanee conti | la tache | france | bourgogne | vosne romanee | red
```

## WineList Draft 匹配输出

`WineListImportNormalizedRow` 新增：

```text
producer_match_score
wine_match_score
vintage_match_score
overall_match_score
decision
```

规则：

```text
>= 95    auto_accepted
80-94    needs_review
< 80     manual_required
```

没有候选对象的新 Producer/Wine/Vintage 仍可作为新 registry entity 进入现有导入流程；这不等于与旧实体合并。

## API

新增只读接口：

```text
GET /registry/aliases
GET /registry/import-mappings
GET /registry/review-queue
GET /registry/quality/findings
```

为前端路径一致性，也提供：

```text
GET /api/registry/aliases
GET /api/registry/import-mappings
GET /api/registry/review-queue
GET /api/registry/quality/findings
```

## Frontend

新增 `Registry Quality` 页面，展示：

- Findings
- Review Queue
- Alias
- Import Mapping

库存导入页的 WineList dry-run 表新增匹配分和 decision。

## Migration

新增 migration：

```text
apps/api/migrations/versions/20260613_0003_registry_foundation.py
```

升级策略：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
```

该 migration：

- 只新增 nullable/default-safe 字段和新表。
- 回填已有 Producer `canonical_key` 和 Wine `wine_identity_key`。
- 不 drop table。
- 不清空数据。
- 不修改 Bottle 外键。
- 不伪造或篡改 `InventoryTransaction`。

## 当前限制

- Review Queue 只展示，不提供 approve/reject UI。
- Alias 只具备模型、记录和只读 API；人工管理动作留到后续。
- `merged_into_id` 不会自动迁移 Bottle 或 Ledger。
- 质量 findings 是增量发现，不会删除旧 finding；后续需要设计关闭/复核流程。
- WineList scoring 是本地规则和已有 registry 数据的匹配分，不代表外部权威酒款数据库。
