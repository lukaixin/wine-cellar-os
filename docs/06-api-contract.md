# API 合同草案

后端建议采用 REST API。先保持简单，后续再补 GraphQL 或复杂查询层。

## Producers

```text
GET    /api/producers
POST   /api/producers
GET    /api/producers/{id}
PATCH  /api/producers/{id}
```

## Wines

```text
GET    /api/wines
POST   /api/wines
GET    /api/wines/{id}
PATCH  /api/wines/{id}
GET    /api/wines/search?q=
```

## Vintages

```text
GET    /api/vintages
POST   /api/vintages
GET    /api/vintages/{id}
PATCH  /api/vintages/{id}
GET    /api/vintages/{id}/drink-windows
POST   /api/vintages/{id}/drink-windows
GET    /api/vintages/{id}/valuations
POST   /api/vintages/{id}/valuations
```

## Bottles

```text
GET    /api/bottles
POST   /api/bottles
GET    /api/bottles/{id}
PATCH  /api/bottles/{id}
POST   /api/bottles/{id}/move
POST   /api/bottles/{id}/drink
POST   /api/bottles/{id}/gift
POST   /api/bottles/{id}/sell
POST   /api/bottles/{id}/damage
GET    /api/bottles/{id}/transactions
POST   /api/bottles/{id}/media
```

## Cellars and locations

```text
GET    /api/cellars
POST   /api/cellars
GET    /api/cellars/{id}
PATCH  /api/cellars/{id}
GET    /api/cellars/{id}/locations
POST   /api/cellars/{id}/locations
GET    /api/cellars/{id}/grid
```

## Dashboard

```text
GET /api/dashboard/summary
GET /api/dashboard/drink-now
GET /api/dashboard/inventory-structure
GET /api/dashboard/valuation
GET /api/dashboard/cellar-occupancy
```

## Import/export

```text
POST /api/import/csv
POST /api/import/excel
GET  /api/export/bottles.csv
GET  /api/export/bottles.xlsx
POST /api/backup/create
POST /api/backup/restore
```

## Label intake

```text
POST /api/intake/label-images
POST /api/intake/label-drafts
POST /api/intake/label-drafts/confirm
```

规则：

- `POST /api/intake/label-images` 接收 multipart `file`，仅允许 jpg/jpeg/png/webp，并保存到本地配置目录。
- `POST /api/intake/label-drafts` 只根据已上传图片生成可编辑草稿；当前实现是 mock filename recognizer，不调用 AI/OCR 或外部 API。
- `POST /api/intake/label-drafts/confirm` 要求用户提交确认后的酒庄、酒款、年份、容量和位置，后端通过 `IN` transaction 创建正式 bottle。
- 上传和草稿阶段不能直接创建正式库存。
- 未来 AI/OCR adapter 仍只能替换草稿生成逻辑，不能绕过用户确认和 ledger。

## 错误返回

统一结构：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "drink_from must be earlier than drink_to",
    "details": {}
  }
}
```
