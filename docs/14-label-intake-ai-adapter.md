# 酒标 Intake 与未来 AI/OCR Adapter 边界

本文件说明当前酒标图片录入能力和未来 AI/OCR 接入边界。核心原则不变：识别结果只能作为草稿，不能直接改变正式库存。

## 当前实现

- 用户在前端“酒标入库”页面上传 jpg/jpeg/png/webp 图片。
- 后端将图片保存到本地数据目录，默认 `data/uploads/labels`。
- 上传记录写入 `label_image_uploads`，保存原始文件名、服务端文件名、content type、大小、sha256、相对路径和可选 `bottle_id`。
- `MockLabelRecognizer` 只根据本地文件名做低置信字段预填，不读取外部网站，不调用 OCR/AI API。
- 生成草稿不会创建 `Bottle`，也不会写 `InventoryTransaction`。
- 用户编辑并确认草稿后，后端通过现有 `InventoryService.create_bottle_with_in_transaction` 写入 `IN` ledger，再把 upload 关联到 bottle。

## 文件与安全规则

- 允许类型：`image/jpeg`、`image/png`、`image/webp`。
- 默认大小上限：5 MB，可通过 `WINE_CELLAR_LABEL_MAX_UPLOAD_BYTES` 配置。
- 上传目录必须解析在 `WINE_CELLAR_DATA_DIR` 内。
- 服务端文件名必须由系统生成，不能用原始文件名覆盖已有文件。
- `data/uploads/labels` 默认不提交真实图片，只保留 `.gitkeep`。

## Adapter 合同

未来真实 OCR/AI adapter 应遵循当前 `LabelRecognizer` 接口：

```text
recognize(upload: LabelImageUpload) -> LabelRecognitionResult
```

返回内容只能包括：

- `recognizer`：adapter 名称。
- `confidence`：`low` / `medium` / `high`。
- `fields`：候选酒庄、酒款、年份、国家、产区、类型、容量、备注。
- `warnings`：来源、置信度、缺失字段或需人工复核的问题。

## 禁止事项

- 不允许 adapter 直接创建或修改 `Bottle`、`Vintage`、`Wine`、`Producer`。
- 不允许 adapter 写入 `InventoryTransaction`。
- 不允许默认上传用户图片到云端。
- 不允许把 API key、cookie、session 写入代码或文档。
- 不允许接入 Wine-Searcher 或受限网站 scraping。
- 不允许把识别结果展示成权威结论；必须保留草稿、来源和置信度。

## 后续可做

- 增加本地 OCR adapter，但默认关闭。
- 增加识别结果来源字段和字段级置信度。
- 增加草稿保存/拒绝历史。
- 增加图片与正式 `media_assets` 的统一关系，但不能替代库存 ledger。
