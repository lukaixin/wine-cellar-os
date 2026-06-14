# Collection Explorer MVP

最后更新：2026-06-14

本文记录 Beta-3A Collection Explorer MVP 的实现边界。Collection Explorer 只回答“我的酒窖里有哪些具体库存瓶、在哪里、是什么状态”，不替代 Registry Search，也不引入价格、适饮期、推荐或分析能力。

## 目标

用户能够在 5 秒内通过关键词和基础筛选找到库存中的任意一瓶酒。

Collection 与 Registry 的边界：

- Registry：系统知道哪些 Producer / Wine / Vintage 存在。
- Collection：用户实际拥有的 Bottle。
- Collection Search 返回 Bottle 维度的库存结果，不返回 Registry Entity 列表。

## API

新增只读接口：

```text
GET /collection/search
GET /collection/bottles/{id}
```

同时提供等价路径：

```text
GET /api/collection/search
GET /api/collection/bottles/{id}
```

### GET /collection/search

Query 参数：

```text
q             可选，支持 Producer / Wine / Vintage / Alias 搜索
producer_id   可选，只筛选指定 Producer
vintage_year  可选，只筛选指定年份
location_id   可选，只筛选指定 Location
status        可选，只筛选指定 Bottle current_status
limit         默认 25，最大 100
offset        默认 0
```

返回结构：

```text
query
total
limit
offset
items[]
```

`items[]` 是库存结果分组，按 `vintage + location + status` 聚合，包含：

```text
bottle_id
bottle_ids
producer_id / producer_name / producer_name_cn
wine_id / wine_name / wine_name_cn
vintage_id / vintage_year / is_non_vintage
bottle_count
location { id, cellar_name, code }
status
```

搜索复用 Registry Search 的匹配思路和规范化函数，并额外支持 `2016 Rayas` 这类跨字段 token 查询。Alias 只用于查找库存，不触发治理动作。

### GET /collection/bottles/{id}

返回单瓶详情：

```text
id
bottle_size_ml
quantity
status
acquisition_date
vintage_id / vintage_year / is_non_vintage
wine_id / wine_name / wine_name_cn
producer_id / producer_name / producer_name_cn
location { id, cellar_name, code }
created_at / updated_at
```

该接口不返回 purchase price、market price、ROI、drink window、rating、recommendation 或复杂分析字段。

## 页面说明

新增 `Collection Explorer` 页面：

- Left：Producer / Vintage / Location / Status filters。
- Top：Collection Search 搜索框。
- Center：Result List，展示 Producer、Wine、Vintage、Bottle Count、Location、Status，并支持分页。
- Right：Bottle Detail Drawer，点击结果行后展示单瓶详情。

页面风格沿用当前 Alpha UI 的 panel、table、drawer-like right panel 和紧凑表单控件。

## 数据流

```text
用户输入搜索或筛选
-> apps/web CollectionExplorerPage
-> GET /collection/search
-> CollectionService 读取 Bottle + Vintage + Wine + Producer + Location
-> RegistryService.search + 本地 token/alias 匹配
-> 返回库存分组结果
-> 用户点击结果行
-> GET /collection/bottles/{id}
-> 右侧详情抽屉展示单瓶详情
```

本轮只读取现有 Bottle 快照字段，不修改 `Bottle.current_status`、`Bottle.current_location_id` 或 `InventoryTransaction`。

## 已知限制

- 搜索仍是本地字符串规则和 registry alias 匹配，不是语义搜索。
- 结果按 `vintage + location + status` 聚合，详情抽屉展示该组中的代表 bottle；完整单瓶逐瓶操作仍走现有 Bottle detail。
- Location filter 当前使用 location id；跨酒柜位置同名时不会混淆，但 URL 可读性一般。
- 不包含价格、估值、适饮、推荐、评分、治理审批或 dashboard 分析。
