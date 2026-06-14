# Beta-5 WS Price Import Extension

最后更新：2026-06-14

## 背景

`WineList.xlsx` 的 `Stock` sheet 新增字段：

```text
WS Price
```

该字段用于记录用户从 Wine-Searcher 侧手工带入的参考价。系统不抓取 Wine-Searcher，也不绕过访问限制。

## 设计决策

`WS Price` 本轮存放在 `Bottle.ws_price`。

理由：

- WineList 导入会把一行 `Quantity` 展开为多瓶具体 `Bottle`，`WS Price` 是这次导入行带来的单瓶参考价，最直接对应每个 Bottle。
- 当前需求要求 Bottle Detail 展示 `ws_price`，并要求 Analytics 计算 `SUM(ws_price)`，放在 Bottle 可以避免按 Vintage 聚合时把多瓶数量和价格来源混淆。
- `Vintage` 表表示酒款年份主数据；把一次导入参考价放到 Vintage 会让同一年份的所有 Bottle 共享同一价格，未来不同来源、不同币种、不同时间点会变得不清晰。
- 独立 `valuation_snapshots` 表已经存在，更适合未来的价格 provider、截图、CSV、历史快照和置信度。本轮不需要把一个导入字段升级成估值历史模型。

因此本轮采用：

```text
bottles.ws_price numeric(12,2) nullable
```

未来如果要做正式价格历史，应继续使用或扩展 `valuation_snapshots`，并记录 source、currency、captured_at、confidence 等来源字段。

## 导入行为

WineList draft：

- 识别 `WS Price` 列。
- 空值允许，导入为 `null`。
- 非数字或负数会作为行级错误。
- draft 响应的 `normalized.ws_price` 会展示解析后的值。

WineList confirm：

- 每个展开出来的 Bottle 都写入对应行的 `ws_price`。
- 仍通过 `InventoryService.create_bottle_with_in_transaction_result` 创建正式 Bottle 和 `IN` ledger。
- 不修改 `InventoryTransaction` schema。

## API 展示

Bottle API：

```text
GET /api/bottles
GET /api/bottles/{id}
```

返回新增：

```text
ws_price
```

Collection Bottle Detail：

```text
GET /collection/bottles/{id}
GET /api/collection/bottles/{id}
```

返回新增：

```text
ws_price
```

Analytics：

```text
inventory.total_ws_value = SUM(bottle.ws_price)
inventory.ws_priced_bottles = COUNT(bottle.ws_price IS NOT NULL)
```

## Migration

新增 Alembic migration：

```text
20260614_0004_bottle_ws_price.py
```

升级路径：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
```

迁移安全性：

- 只新增 nullable 字段。
- 不删除数据。
- 不重写 Bottle 外键。
- 不伪造或改写 `InventoryTransaction` 历史。

## 已知限制

- `ws_price` 默认按 CNY 展示；本轮不新增币种字段。
- 不支持价格历史、市场波动、ROI、gain/loss 或 portfolio return。
- 不提供 Wine-Searcher API 或爬虫。
- 空值表示该 Bottle 没有导入 WS Price，不代表价格为 0。
