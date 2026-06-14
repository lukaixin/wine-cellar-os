# WineList 真实库存导入规则

最后更新：2026-06-13

本文记录 Alpha 版真实库存导入的第一版边界。目标是安全导入 `data/sample/WineList.xlsx` 的真实库存样例，同时保留本地数据、ledger 审计和后续 migration 能力。

## 支持范围

- 只解析 `WineList.xlsx` 的 `Stock` sheet。
- 不导入 `HKStock`、shipment、盲品、价格参考、Burgundy vintage report 或透视汇总表。
- 不调用外部 API，不抓取 Wine-Searcher，不写入自动估值。
- 不新增独立 `WineRegistry` 表；现有 `Producer -> Wine -> Vintage` 是第一版 registry。
- 所有正式库存创建都必须通过 `InventoryService` 写入 Bottle 和对应 `IN` transaction。

## 导入流程

1. 上传 `.xlsx` 后进入 draft 阶段。
2. Draft 会校验表头、必填字段、年份、数量、成本、Style 和位置映射。
3. Draft 会写入 `import_batches` 和 `import_batch_rows`，保存文件 hash、原始行、规范化行、错误和 warning。
4. Draft 不创建 Producer、Wine、Vintage、Bottle 或 InventoryTransaction。
5. Draft 会记录 registry import mapping、匹配分和需要人工关注的 registry review queue。
6. Confirm 必须在全部行有效时执行。
7. Confirm 使用单个数据库事务；任意一瓶写入失败，整批 rollback。
8. Confirm 会创建或复用三个 coarse location，再通过 `IN` ledger 展开每瓶库存。
9. 导入完成后可在前端 `Import Batch History` 查看批次列表和行级 review。

## 审计 API

当前提供只读审计接口：

```text
GET /imports/batches?limit=20&offset=0
GET /imports/batches/{batch_id}
```

为保持前端 API 路径一致，也提供等价 `/api/imports/batches` 和 `/api/imports/batches/{batch_id}`。

批次列表返回：

- batch id、filename、status、created_at、confirmed_at。
- total_rows、success_rows、warning_rows、error_rows。
- created_bottle_count。

批次详情返回：

- batch 基本信息和文件 hash。
- row_number、raw values、parsed producer/wine/vintage、quantity。
- row warnings、row errors。
- created_bottle_ids 和 ledger_transaction_ids。

这些接口不提供删除、回滚或直接修正库存能力。

## Registry 匹配分

WineList draft 行新增：

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
80-94    needs_review，并进入 registry_review_queue
< 80     manual_required
```

没有候选对象的新 Producer/Wine/Vintage 会作为新 registry entity 继续现有导入流程；这不是自动合并。Alias 只有 `approved` 状态才能用于稳定匹配，冲突 alias 会进入 review queue。

## 字段映射

| `Stock` 列 | 目标字段 |
| --- | --- |
| `Producer` | `Producer.name_original`；规范化后匹配复用，原始拼写保留 |
| `Wine` | `Wine.name_original`；空值时使用 `Producer` 作为酒款名并记录 warning |
| `Country` | `Producer.country` 和 `Wine.country` |
| `Region` | `Producer.region` 和 `Wine.region`；`Sorthern Rhone` 会规范化为 `Southern Rhone` |
| `Sub-Region` | `Wine.appellation` |
| `Style` | `Wine.type`，映射为 `red/white/rose/sweet/fortified/sparkling/other` |
| `Vintage` | `Vintage.vintage_year` |
| `Quantity` | 展开为 N 个 Bottle，每瓶一条 `IN` transaction |
| `Cost` | `Bottle.purchase_price`，默认 `purchase_currency='CNY'` |
| `Channel` | `Bottle.purchase_channel` |
| `WS Price` | 暂不导入，后续进入 `ValuationSnapshot` |
| `No`, `Total` | 不作为业务字段，只保存在 import row 原始 JSON |

## 位置映射

| 来源条件 | Cellar | Location | Bottle 状态 |
| --- | --- | --- | --- |
| `Status=FR` | `法国朋友家` | `FR` | `in_stock` |
| `CAVE=C` | `家中酒柜` | `C` | `in_stock` |
| `Status` 和 `CAVE` 均为空 | `家中散放` | `HOME-OUTSIDE` | `in_stock` |

如果目标 location 已存在但容量不足，confirm 会失败并 rollback。系统不会自动删除或覆盖已有 location。

## 重复导入规则

- 同一文件同一 source row 已确认后，再次 draft 会把对应行标记为 invalid。
- 同一 Producer/Wine/Vintage 在 Excel 中出现多行不是错误，可能代表不同位置或多个库存批次。
- 同一行的 `Quantity > 1` 会展开为多个 Bottle，而不是数量字段。

## 数据安全

正式导入真实库存前必须先备份本地 SQLite：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
```

不要提交真实 SQLite、真实成本数据、真实酒标图片或导入后的本地数据库文件。导入结果只应存在本地数据库和本地备份中。

## 当前限制

- 只支持当前样例 `Stock` sheet 的结构，不是通用 Excel 导入器。
- 不提供批次撤销或 rollback wizard。后续如需撤销，应通过 ledger 补偿交易或专门的安全回滚流程，不应删除原 transaction。
- 空 `Wine` 行当前按 `Producer` 同名酒款处理，后续可增加人工映射确认。
- `WS Price` 暂不进入估值表，避免把样例价误写成权威市场价格。
- 三个 coarse location 只是第一版落点；如果后续需要精确格子，应通过 MOVE ledger 调整。
