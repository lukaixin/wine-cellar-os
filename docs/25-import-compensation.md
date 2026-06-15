# Beta-6 Import Compensation

最后更新：2026-06-14

## 目标

Import Compensation 用于处理 WineList 批次误导入。它不是删除、回滚或改写历史，而是为已确认 import batch 生成可审计的补偿交易，让库存快照与 ledger 继续保持一致。

典型场景：

- 导入了错误批次。
- Vintage、Producer、Wine 或 Quantity 后续发现错误。
- 用户希望撤销该批次对当前库存的影响，但仍保留历史导入事实。

## 核心规则

- 不删除 `InventoryTransaction` 历史记录。
- 不改写原始 `IN` ledger。
- 不直接删除 `Bottle`。
- 补偿动作必须通过 `InventoryService.apply_transaction()` 写入 `ADJUST` transaction。
- 原始导入历史、补偿原因、补偿交易 ID 均保留在 import batch 审计记录中。

## 数据模型

`import_batches` 新增以下字段：

- `compensated_at`
- `compensation_reason`
- `compensation_transaction_ids`

这些字段只记录批次是否已补偿及补偿交易集合，不改变原始 batch `status`，也不删除 `import_batch_rows` 中的 source row、created bottle ids 或 original import transaction ids。

## API

### Import Batch Detail

`GET /imports/batches/{batch_id}`

等价路径：

`GET /api/imports/batches/{batch_id}`

新增字段：

- `compensated_at`
- `compensation_reason`
- `compensation_transaction_ids`
- `can_compensate`
- `compensation_blockers`
- `compensated_bottle_count`

### Compensate Import Batch

`POST /imports/batches/{batch_id}/compensate`

等价路径：

`POST /api/imports/batches/{batch_id}/compensate`

请求体：

```json
{
  "reason": "导入了错误批次",
  "confirm_bottle_count": 119
}
```

响应：

```json
{
  "batch_id": "batch-id",
  "compensated_bottles": 119,
  "compensation_transaction_ids": ["transaction-id"],
  "compensated_at": "2026-06-14T00:00:00Z",
  "transaction_type": "ADJUST",
  "status": "compensated"
}
```

## 补偿算法

系统先从 `import_batch_rows.created_bottle_ids` 与 `created_transaction_ids` 生成补偿计划。

每个可补偿 bottle 必须满足：

- import batch `status == confirmed`。
- batch 尚未补偿。
- row 中 created bottle 数量与 original `IN` transaction 数量一致。
- bottle 仍存在。
- bottle `current_status == in_stock`。
- bottle 仍有 `current_location_id`。
- original transaction 存在，且为同一 bottle 的 `IN` transaction。
- bottle 除 original `IN` 之外没有任何 post-import ledger activity。

补偿执行时，每个 bottle 生成一条：

- `transaction_type = ADJUST`
- `from_location_id = bottle.current_location_id`
- `to_location_id = null`
- `actor = import_compensation`
- `reason = Import batch compensation: {batch_id}`
- `note = Compensated import batch {batch_id}: {reason}`

`ADJUST` 会把 bottle 快照同步为不可用状态并清空当前位置。原始 `IN` transaction 和导入行审计记录仍保留。

## 阻止条件

以下情况会拒绝补偿：

- batch 不是 `confirmed`。
- batch 已经补偿过。
- batch 没有 created bottle ids。
- created bottle ids 与 original transaction ids 数量不一致。
- bottle 已被 consume、gift、damage、move 或 adjust。
- bottle 缺失或 current location 缺失。
- original import transaction 缺失、类型不是 `IN`，或不属于该 bottle。
- `confirm_bottle_count` 与影响瓶数不一致。

拒绝时不写入任何补偿 ledger。

## UI

库存导入页的 `Import Batch Detail` 增加 Compensation 区域：

- 显示影响瓶数。
- 显示 original `IN` ledger 数量。
- 显示补偿 ledger 数量。
- 显示是否可补偿与 blockers。
- 要求填写补偿原因。
- 点击 `Compensate` 前使用浏览器二次确认。

## 迁移

迁移文件：

`apps/api/migrations/versions/20260614_0005_beta6_safety_foundation.py`

迁移策略：

- 只新增 nullable 字段。
- 不删除旧列。
- 不重写历史 import batch。
- 不生成任何库存 transaction。

## 验证

推荐命令：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python -m pytest tests\test_winelist_import.py tests\test_migrations.py -q
```

覆盖重点：

- 已确认 WineList batch 可生成 `ADJUST` 补偿 ledger。
- 原始 `IN` ledger 保留。
- bottle 快照与 ledger 补偿结果一致。
- 已发生后续库存活动的 batch 被拒绝补偿。
- 已补偿 batch 不允许重复补偿。

## 非目标

- 不做删除式 rollback。
- 不修改 Registry domain。
- 不修改 Analytics 逻辑。
- 不为 CSV import 建立完整批次补偿流。
- 不自动修复 Producer/Wine/Vintage 主数据错误。
