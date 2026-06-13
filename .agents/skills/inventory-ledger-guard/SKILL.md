---
name: inventory-ledger-guard
description: Guard inventory audit invariants for Wine Cellar OS. Use when Codex touches bottle status, location moves, ledger transactions, CSV confirm, label-confirmed intake, or any workflow that could bypass InventoryTransaction rules.
---

# name

inventory-ledger-guard

## description

用于保护 Wine Cellar OS 的库存审计边界。任何触及入库、出库、移动、盘点、标签确认入库、CSV confirm 的改动，都应先经过这套 ledger 守卫检查。

## when to use

- 修改 `InventoryService`、inventory 相关 router、schema、前端库存操作表单时。
- 评审 CSV 导入确认、酒标确认入库、MOVE / CONSUME / GIFT / DAMAGE / ADJUST 行为。
- 检查某个改动是否绕过了 `InventoryTransaction`。
- 编写或评审库存一致性测试。

## when not to use

- 不用于纯读接口、只读 dashboard、估值快照或 drink window 设计。
- 不用于纯文档整理或样式调整。
- 不用于不涉及库存状态和位置变化的 registry 清洗任务。

## required checks

- 先读取 `AGENTS.md`、`docs/12-inventory-rules.md`、`docs/04-data-model.md`。
- 验证所有库存变化都生成 `InventoryTransaction`，不能只改 `Bottle.current_status` 或 `Bottle.current_location_id`。
- 验证 `MOVE` / `CONSUME` / `GIFT` / `DAMAGE` 只允许作用于 `in_stock` bottle。
- 验证 `from_location_id` / `to_location_id`、位置容量、当前位置匹配等约束没有被绕过。
- 验证 UI 和 API 不会允许同一瓶重复出库，且 `ADJUST` 保留 correction note。
- 若改动触及导入或酒标流程，确认“草稿”和“正式库存”边界仍然清晰。

## expected final output

- 一份 ledger 守卫检查结论，说明哪些不变量被验证。
- 若发现风险，明确指出会破坏哪条库存规则以及阻断建议。
- 若有改动，给出对应测试/验证命令和残余风险说明。
