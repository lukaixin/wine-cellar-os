# Beta-5 Analytics Foundation

最后更新：2026-06-14

## 范围

Beta-5 新增只读 Analytics Foundation，用于查看本地库存、消费和近期活动的基础统计。

本轮只做：

- Inventory Summary
- Country / Region / Vintage / Status Distribution
- Consumption Summary
- Monthly Consumption Trend
- Recent Activity

本轮不做：

- 消费预测
- 价格预测
- ROI / gain-loss / portfolio return
- AI sommelier / pairing / recommendation
- 独立统计表

## API

新增只读 API：

```text
GET /analytics/summary
GET /api/analytics/summary
```

Query：

```text
recent_limit integer, default 20, min 1, max 100
```

响应结构：

```text
inventory
  total_bottles
  total_wines
  total_producers
  total_vintages
  total_ws_value
  ws_priced_bottles
  country_distribution
  region_distribution
  vintage_distribution
  status_distribution

consumption
  periods
    last_30_days
    last_90_days
    all_time
  monthly_trend

activity
  recent ledger events
```

## 数据来源

Inventory Overview 使用当前 Bottle 查询快照与 Producer / Wine / Vintage 关系运行时聚合。

Consumption 与 Activity 直接读取 `InventoryTransaction`：

- `CONSUME` -> consumed bottles
- `GIFT` -> gifted bottles
- `DAMAGE` -> damaged bottles
- `IN` -> recent activity 中显示为 Import
- `MOVE` -> recent activity 中显示为 Move

没有新增统计缓存表。所有数据在请求时计算。

## UI

新增前端页面：

```text
Analytics
```

页面分为：

- Overview：总瓶数、酒款、生产者、年份、Total WS Value 和基础分布。
- Consumption：Last 30 Days / Last 90 Days / All Time，以及按月汇总趋势。
- Activity：最近的 Import / Consume / Gift / Move / Damage ledger 事件。

## 已知限制

- Inventory 分布基于当前 Bottle 快照；快照由 ledger-backed 写路径维护。
- Consumption 不做预测，只统计已经发生的 ledger 事件。
- Monthly Trend 只按月份聚合，不提供复杂时间序列分析。
- Total WS Value 只是 `SUM(bottle.ws_price)`，不代表投资回报或市场估值。

## 验证

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python -m pytest -q

cd D:\MyLife\17_葡萄酒管理系统\apps\web
npm.cmd run build
npm.cmd run test:ui
npm.cmd run qa:alpha
```
