# Bottle Detail & Timeline

最后更新：2026-06-14

本文记录 Beta-3B Bottle Detail & Timeline 的实现边界。目标是在 Collection Explorer 中形成 `Group -> Bottle -> Timeline` 的只读查看链路，让用户能从库存分组进入具体单瓶，并看到该瓶来自真实 Inventory Transaction Ledger 的历史事件。

## Bottle Detail

只读接口：

```text
GET /collection/bottles/{id}
GET /api/collection/bottles/{id}
```

返回字段聚焦在库存身份和当前位置：

```text
id / bottle_id
status
quantity
bottle_size_ml
producer_id / producer_name / producer_name_cn
wine_id / wine_name / wine_name_cn
vintage_id / vintage_year / is_non_vintage
location { id, cellar_name, code }
acquisition_date
created_at / updated_at
```

该接口不返回 purchase price、估值、ROI、drink window、推荐、治理状态或可编辑字段。本轮没有新增数据库字段，也没有修改 `Bottle.current_status`、`Bottle.current_location_id` 或库存数量。

## Timeline API

新增只读接口：

```text
GET /collection/bottles/{id}/timeline
GET /api/collection/bottles/{id}/timeline
```

Timeline 只从 `inventory_transactions` 读取，不新增独立历史表。返回按 `event_time` 倒序排列：

```text
event_type
event_time
quantity_delta
reference_type
reference_id
from_location { id, cellar_name, code }
to_location { id, cellar_name, code }
notes
```

`reference_type` 固定为 `inventory_transaction`，`reference_id` 是对应 ledger transaction id。`quantity_delta` 仅用于展示：

```text
IN -> +1
CONSUME / GIFT / DAMAGE -> -1
MOVE / ADJUST -> 0
```

如果 bottle 存在但没有 ledger 记录，接口返回空数组。该情况通常只用于兼容历史数据或测试 fixture；正常库存写入仍必须通过 `InventoryService` 生成 ledger。

## UI Flow

Collection Explorer 结果仍按 `vintage + location + status` 分组展示。每个 group 行可以展开组内 Bottle：

```text
Group
  Bottle #1
  Bottle #2
  Bottle #3
```

用户点击具体 Bottle 后，右侧 Bottle Detail Drawer 加载：

```text
Detail tab
Timeline tab
```

Detail tab 展示单瓶身份、位置、入库日期和 registry link id。Timeline tab 按时间倒序展示该瓶库存事件，包含事件类型、时间、位置变化、数量变化和 notes。Timeline 只读、可滚动，不提供 Consume、Gift、Move、Damage、Delete、Merge 或任何库存写操作入口。

## Known Limitations

- Timeline 事件名称仍使用现有 transaction type 映射，不单独推导 `Import`、`Create Bottle`、`Manual Correction` 等更细 display category。
- `ADJUST` 的 `quantity_delta` 当前统一展示为 `0`，因为现有 ledger 没有单独的 delta 字段；具体含义依赖 from/to location 和 notes。
- 空 timeline 仅作为兼容路径存在；新库存仍应通过 ledger workflow 创建。
- Group 内 Bottle 子项当前使用 `Bottle #n` 和短 id 展示，后续可补充 acquisition date、location diff 或 import provenance，但本轮不扩展分析或治理信息。
- 本轮不新增 schema、不实现库存写操作、不新增 registry governance、不新增 analytics。
