# ADR-0002：库存采用 Ledger 模型

## 状态

Accepted.

## 背景

酒窖管理不是简单数量统计。用户需要知道每瓶酒何时入库、移动、喝掉、送礼、损耗或盘点调整。若只维护库存数量，历史无法追溯，后续消耗分析和资产报告也不可靠。

## 决策

所有库存变化必须通过 `InventoryTransaction`。`Bottle.current_status` 和 `Bottle.current_location_id` 只是当前快照。

## 后果

优点：

- 可审计。
- 可做盘点差异。
- 可做消耗分析。
- 可追踪礼赠和移动历史。

缺点：

- 实现略复杂。
- 需要服务层统一管控状态变化。

## 实现要求

- 禁止 endpoint 直接修改库存状态。
- 所有库存操作必须经过 `InventoryService`。
- 测试必须覆盖状态转移和 transaction 生成。
