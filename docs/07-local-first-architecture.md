# 本地优先技术架构

## 目标

先做可在本机运行的 MVP，同时保留未来迁移到云端和多设备同步的可能。

## 推荐架构

```text
Browser / PWA
    ↓
Local API Server: FastAPI
    ↓
SQLite database + local media directory
```

## 为什么本地优先

- 藏酒价值、购买价、送礼对象、库存照片属于敏感信息。
- 初期用户少，本地部署成本低。
- 不需要先处理账号、支付、云安全、多租户。
- 更适合快速迭代真实酒柜场景。

## 后端结构建议

```text
apps/api/
  pyproject.toml
  app/
    main.py
    core/
      config.py
      database.py
      errors.py
    models/
      producer.py
      wine.py
      vintage.py
      bottle.py
      cellar.py
      location.py
      transaction.py
      valuation.py
      media.py
      tag.py
    schemas/
    services/
      inventory_service.py
      drink_window_service.py
      valuation_service.py
      dashboard_service.py
    routers/
    migrations/
  tests/
```

## 前端结构建议

```text
apps/web/
  package.json
  src/
    app/
    components/
    features/
      dashboard/
      cellar-grid/
      bottles/
      intake/
      transactions/
      valuations/
    lib/
    types/
```

## 数据一致性规则

所有会改变库存的操作必须进入 `InventoryService`，禁止多个 API endpoint 直接改 `Bottle.current_status` 或 `current_location_id`。

建议服务方法：

```text
create_bottle_with_purchase_in()
move_bottle()
drink_bottle()
gift_bottle()
sell_bottle()
mark_damaged()
adjust_stocktake()
```

## 媒体文件规则

```text
assets/
  label-images/
    yyyy/
      mm/
        {uuid}.{ext}
  screenshots/
```

数据库保存：

- file_path
- file_hash
- mime_type
- owner_type
- owner_id
- media_type

## 价格 provider 规则

```text
PriceProvider interface
  get_snapshot(query) -> ValuationSnapshotDraft

Implementations:
  ManualPriceProvider
  CsvImportPriceProvider
  ScreenshotNoteProvider
  LinkNoteProvider

Future:
  LicensedWineSearcherProvider
  LivExProvider
  MerchantQuoteProvider
```

不要把外部平台页面结构写死进核心服务。

## 迁移策略

- SQLite MVP。
- 数据库访问层不要依赖 SQLite 独有行为，除 FTS 搜索外。
- 未来迁移 Postgres 时，保留 UUID 主键、created_at/updated_at、明确外键。
- 本地媒体未来可迁移对象存储，但 MVP 不需要。
