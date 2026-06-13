# 库存状态与 Transaction 规则

本项目使用 `Bottle.current_status` 和 `Bottle.current_location_id` 作为查询快照，真实历史以 `InventoryTransaction` 为准。任何库存变化都必须生成 transaction，不允许只改 bottle 快照。

## Bottle 状态

- `in_stock`：在库，可移动、饮用、送礼、损耗。
- `drunk`：已饮用，不可再次出库。
- `gifted`：已送礼，不可再次出库。
- `damaged`：损耗，不可再次出库。
- `lost`：盘亏或盘点未找到，不可再次出库。
- `sold` / `returned`：预留状态，后续扩展时仍必须通过 transaction 记录。

## 支持的 Transaction 类型

- `IN`：入库，必须有 `to_location_id`，会将 bottle 设为 `in_stock`。
- `MOVE`：移动，要求 bottle 当前为 `in_stock`，必须有目标位置，且 `from_location_id` 必须等于 bottle 当前位置。
- `CONSUME`：饮用，要求 bottle 当前为 `in_stock`，完成后状态为 `drunk` 并清空当前位置。
- `GIFT`：送礼，要求 bottle 当前为 `in_stock`，完成后状态为 `gifted` 并清空当前位置。
- `DAMAGE`：损耗，要求 bottle 当前为 `in_stock`，完成后状态为 `damaged` 并清空当前位置。
- `ADJUST`：盘点调整，必须填写备注；有 `to_location_id` 时用于纠正为在库位置，无 `to_location_id` 时用于标记盘亏。

## 校验原则

1. MOVE、CONSUME、GIFT、DAMAGE 都只能作用于 `in_stock` bottle。
2. 对已饮用、已送礼、已损耗或盘亏的 bottle 再次执行出库类 transaction，必须拒绝。
3. MOVE 的 `from_location_id` 必须匹配 bottle 当前 `current_location_id`，避免用过期页面覆盖真实位置。
4. MOVE 的 `to_location_id` 不能与当前位置相同。
5. ADJUST 必须保留 correction note，便于审计盘点原因。
6. Bottle 详情页应展示完整 transaction 时间线，不能只展示当前状态。
7. 新增 bottle 或 MOVE 到目标位置时，目标 location 的在库瓶数不能超过 `capacity`。

## 前端 UX 规则

- Bottle detail 提供 MOVE、CONSUME、GIFT、DAMAGE、ADJUST 明确操作按钮。
- 非 `in_stock` bottle 禁止 MOVE、CONSUME、GIFT、DAMAGE，只允许 ADJUST。
- Cellar grid 需要区分 occupied / empty location，并允许点击位置查看该位置 bottle。
- 在库但无位置、在库但位置不存在、非在库但仍有关联位置，都应作为位置异常提示。
