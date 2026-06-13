# 数据模型草案

## 建模原则

1. `Wine`、`Vintage`、`Bottle` 必须分开。
2. 库存变化必须通过 `InventoryTransaction` 记录。
3. 价格、适饮期、识别结果都要保留来源和置信度。
4. 图片不直接存数据库，数据库只存路径、hash、类型和关联对象。
5. 预留 LWIN 字段，但不强依赖。

## ER 概念

```text
Producer 1─n Wine 1─n Vintage 1─n Bottle
Bottle n─1 Location n─1 Cellar
Bottle 1─n InventoryTransaction
Vintage 1─n DrinkWindow
Vintage 1─n ValuationSnapshot
Bottle 1─n MediaAsset
Wine/Vintage/Bottle n─n Tag
```

## 核心表

### producers

```text
id uuid pk
name_original text not null
name_cn text nullable
country text nullable
region text nullable
website text nullable
aliases json/text nullable
created_at datetime
updated_at datetime
```

### wines

```text
id uuid pk
producer_id uuid fk producers.id
name_original text not null
name_cn text nullable
type text nullable          # red/white/sparkling/rose/sweet/fortified/other
color text nullable
country text nullable
region text nullable
appellation text nullable
grape_varieties json/text nullable
classification text nullable
lwin7 text nullable
aliases json/text nullable
created_at datetime
updated_at datetime
```

### vintages

```text
id uuid pk
wine_id uuid fk wines.id
vintage_year integer nullable  # NV 可为空或使用 null + is_non_vintage
is_non_vintage boolean default false
lwin11 text nullable
critic_score numeric nullable
critic_source text nullable
default_drink_from integer nullable
default_drink_to integer nullable
drink_window_confidence text nullable # low/medium/high
notes text nullable
created_at datetime
updated_at datetime
unique(wine_id, vintage_year, is_non_vintage)
```

### cellars

```text
id uuid pk
name text not null
cellar_type text not null    # cabinet/room/shelf/box_area/other
rows integer nullable
columns integer nullable
temperature_target numeric nullable
humidity_target numeric nullable
notes text nullable
created_at datetime
updated_at datetime
```

### locations

```text
id uuid pk
cellar_id uuid fk cellars.id
code text not null           # A-03-05, Box-01, Shelf-2
row_index integer nullable
column_index integer nullable
layer_index integer nullable
position_note text nullable
capacity integer default 1
location_type text default 'grid' # grid/shelf/box/freeform
created_at datetime
updated_at datetime
unique(cellar_id, code)
```

### bottles

```text
id uuid pk
vintage_id uuid fk vintages.id
bottle_size_ml integer default 750
lwin16 text nullable
acquisition_date date nullable
purchase_price numeric nullable
purchase_currency text default 'CNY'
purchase_source text nullable
purchase_channel text nullable
condition text nullable       # excellent/good/label_damage/low_fill/etc
current_status text not null  # in_stock/drunk/gifted/sold/damaged/lost/returned
current_location_id uuid fk locations.id nullable
personal_rating integer nullable
personal_notes text nullable
created_at datetime
updated_at datetime
```

### inventory_transactions

```text
id uuid pk
bottle_id uuid fk bottles.id
transaction_type text not null
from_location_id uuid fk locations.id nullable
to_location_id uuid fk locations.id nullable
occurred_at datetime not null
actor text nullable
reason text nullable
note text nullable
created_at datetime
```

### valuation_snapshots

```text
id uuid pk
vintage_id uuid fk vintages.id
bottle_size_ml integer default 750
source text not null          # manual/csv/screenshot/wine_searcher_note/livex_future/etc
source_url text nullable
region text nullable
currency text not null
low_price numeric nullable
avg_price numeric nullable
median_price numeric nullable
tax_included boolean nullable
shipping_included boolean nullable
captured_at datetime not null
confidence text default 'low'
notes text nullable
created_at datetime
```

### drink_windows

```text
id uuid pk
vintage_id uuid fk vintages.id
source text not null          # manual/rule/critic/ai
source_detail text nullable
drink_from integer nullable
drink_to integer nullable
peak_from integer nullable
peak_to integer nullable
confidence text default 'low'
notes text nullable
created_at datetime
updated_at datetime
```

### media_assets

```text
id uuid pk
owner_type text not null      # bottle/wine/vintage/transaction
owner_id uuid not null
media_type text not null      # front_label/back_label/receipt/open_bottle/screenshot/other
file_path text not null
file_hash text nullable
mime_type text nullable
width integer nullable
height integer nullable
captured_at datetime nullable
created_at datetime
```

### label_image_uploads

当前 Alpha 已实现的酒标 intake 上传记录。它只保存本地上传元数据和可选的确认后 `bottle_id`，不代表 AI/OCR 权威识别结果。

```text
id uuid pk
original_filename text not null
stored_filename text unique not null
content_type text not null        # image/jpeg/image/png/image/webp
size_bytes integer not null
sha256 text not null
file_path text not null           # relative to configured data dir
bottle_id uuid nullable fk bottles.id
created_at datetime
```

规则：

- 文件必须存储在配置的数据目录内，默认 `data/uploads/labels`。
- `stored_filename` 使用服务端生成名称，不使用原始文件名覆盖。
- 上传和草稿阶段不创建 `Bottle` 或 `InventoryTransaction`。
- 用户确认草稿后，才通过 `IN` transaction 创建正式 bottle，并回填 `bottle_id`。

### tags

```text
id uuid pk
name text unique not null
category text nullable        # preference/occasion/risk/purchase/etc
created_at datetime
```

### object_tags

```text
id uuid pk
tag_id uuid fk tags.id
owner_type text not null      # wine/vintage/bottle
owner_id uuid not null
created_at datetime
unique(tag_id, owner_type, owner_id)
```

## 库存状态与 transaction 的关系

`bottles.current_status` 是当前状态快照，便于查询。真实历史以 `inventory_transactions` 为准。

示例：

```text
purchase_in: bottle.current_status = in_stock, to_location_id required
drink_out: bottle.current_status = drunk, from_location_id required, current_location_id = null
transfer: current_status 不变，from/to required, current_location_id = to_location_id
gift_out: current_status = gifted, current_location_id = null
stocktake_adjustment: 记录盘点差异，不直接删除历史
```

## 约束

- `drink_from <= drink_to`。
- `peak_from <= peak_to`。
- 出库类 transaction 必须有 `from_location_id`。
- 入库类 transaction 必须有 `to_location_id`。
- `Bottle` 删除应软删除或禁止删除，除非没有任何 transaction。
