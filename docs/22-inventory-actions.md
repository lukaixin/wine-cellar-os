# Beta-4 Inventory Actions

最后更新：2026-06-14

## 目标

Beta-4 将 Bottle Detail Drawer 从只读 Timeline 推进到可写库存事件入口，支持四个动作：

- `Consume`：饮用。
- `Gift`：送礼。
- `Move`：移动位置。
- `Damage`：损耗。

所有动作都必须写入 `InventoryTransaction` ledger，再由 `InventoryService` 同步维护 `Bottle.current_status` 和 `Bottle.current_location_id` 查询快照。禁止绕过 ledger 直接修改库存状态或位置。

## Action Types

| Action | Ledger `transaction_type` | Bottle snapshot 结果 |
| --- | --- | --- |
| Consume | `CONSUME` | `current_status = drunk`，清空 `current_location_id` |
| Gift | `GIFT` | `current_status = gifted`，清空 `current_location_id` |
| Damage | `DAMAGE` | `current_status = damaged`，清空 `current_location_id` |
| Move | `MOVE` | `current_status` 保持 `in_stock`，`current_location_id = to_location` |

`Gift.recipient` 写入 transaction `reason`，格式为 `Recipient: <name>`。`Damage.reason` 写入 transaction `reason`。用户备注写入 transaction `note`。Timeline 会合并展示 `reason` 和 `note`。

## API

四个动作同时提供无 `/api` 和 `/api` 前缀路径：

```text
POST /inventory/actions/consume
POST /api/inventory/actions/consume
POST /inventory/actions/gift
POST /api/inventory/actions/gift
POST /inventory/actions/damage
POST /api/inventory/actions/damage
POST /inventory/actions/move
POST /api/inventory/actions/move
```

### Consume

```json
{
  "bottle_id": "bottle-id",
  "quantity": 1,
  "notes": "Weekend dinner"
}
```

### Gift

```json
{
  "bottle_id": "bottle-id",
  "quantity": 1,
  "recipient": "John",
  "notes": "Birthday"
}
```

### Damage

```json
{
  "bottle_id": "bottle-id",
  "quantity": 1,
  "reason": "Cork damage",
  "notes": "Leaked in storage"
}
```

### Move

```json
{
  "bottle_id": "bottle-id",
  "from_location": "location-id-a",
  "to_location": "location-id-b",
  "notes": "Cabinet B"
}
```

响应复用 `InventoryTransactionRead`，便于前端和测试直接核对 ledger 事件。

## Validation Rules

- `Consume`、`Gift`、`Damage` 的 `quantity` 必须是 `1`。当前 `Bottle` 表示单瓶实例，不支持对一条 Bottle 记录扣减多瓶。
- `quantity <= 0` 会被 schema 拒绝。
- `quantity > 1` 会被 action API 拒绝，防止超额扣减。
- 四个动作只允许作用于 `in_stock` bottle。
- `Consume`、`Gift`、`Damage` 必须能从 bottle 当前状态得到 `from_location_id`，并且完成后清空当前位置。
- `Move.from_location` 必须等于 bottle 当前 `current_location_id`，防止过期页面覆盖真实位置。
- `Move.to_location` 必须存在，不能等于当前位置，并且不能超过目标 location capacity。
- 重复出库、无效 location、已出库后移动都会返回错误，不产生 ledger。

## Timeline Integration

Timeline API 不改协议：

```text
GET /collection/bottles/{bottle_id}/timeline
GET /api/collection/bottles/{bottle_id}/timeline
```

新增 action 仍然只通过 `InventoryTransaction` 进入 Timeline：

- `CONSUME` / `GIFT` / `DAMAGE` 的 `quantity_delta = -1`。
- `MOVE` 的 `quantity_delta = 0`，展示 from/to location。
- Timeline notes 使用 `reason` 和 `note` 合并显示。

Bottle Detail Drawer 新增 `Actions` tab。提交成功后前端会刷新：

- 当前 Bottle Detail。
- 当前 Bottle Timeline。
- Collection Search 结果。
- 全局 app data，包括 Dashboard、Bottle list、Transaction list。

## Non Goals

本轮不实现：

- Consumption Dashboard、统计报表或 analytics。
- Registry Review、alias approve/reject、merge 或冲突处理。
- Purchase Price、Market Price、ROI 或估值。
- Drink Window、Ready To Drink、Aging Curve。
- 推荐、AI Sommelier、Food Pairing。

## Migration Strategy

不需要数据库迁移。Beta-4 复用已有 `inventory_transactions`、`bottles.current_status` 和 `bottles.current_location_id`。
