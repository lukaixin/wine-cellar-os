# 项目进度

最后更新：2026-06-13

## 2026-06-13 更新：WineList 真实库存导入

- 新增 `WineList.xlsx` 的 `Stock` sheet 导入 workflow：draft 阶段只解析、校验并写入 import batch 审计记录，confirm 阶段才创建正式库存。
- 新增 `import_batches` 和 `import_batch_rows` Alembic migration，用于保存来源文件、sheet、文件 hash、原始行、规范化行、warning/error、创建的 bottle id 和 transaction id。
- WineList confirm 使用单个数据库事务，并通过 `InventoryService(..., commit=False)` 为每个展开后的 Bottle 生成 `IN` transaction；任意写入失败会整批 rollback。
- `Stock.Quantity` 会展开为独立 Bottle；`Cost` 写入 `Bottle.purchase_price`，币种默认 `CNY`；`Channel` 写入 `purchase_channel`；`WS Price` 暂不导入估值。
- 位置映射已固定为 `法国朋友家 / FR`、`家中酒柜 / C`、`家中散放 / HOME-OUTSIDE`。空 `Wine` 行按 `Producer` 同名酒款处理并记录 warning。
- 前端“库存导入”页已新增 WineList Excel dry-run、位置汇总、registry 预览和确认入口，同时保留 CSV 草稿导入。
- 新增 Import Batch Review：`GET /imports/batches` 和 `GET /imports/batches/{batch_id}` 支持查看批次列表、分页、行级 raw/parsed/warning/error，以及 created bottle ids 和 ledger transaction ids；前端同页展示 `Import Batch History` 和 `Import Batch Detail`。

## 2026-06-13 更新：项目级 Codex skills 与样例画像脚本

- 新增项目级 repo skills：`wine-registry-normalization`、`inventory-ledger-guard`、`sample-inventory-profiler`、`valuation-snapshot-design`、`migration-safety-review`、`alpha-qa-regression`，统一沉淀常见 Wine Cellar OS 工作流。
- 所有 skills 均放在 `.agents/skills/` 下，明确了适用场景、非适用场景、必查约束和期望交付物，便于后续 Codex 任务直接复用。
- 新增只读样例分析脚本 `scripts/profile_wine_sample.py`，可直接解析 `data/sample/WineList.xlsx` 的 sheet、列、空值、唯一值和基础分布，不依赖外部 API，也不改写样例文件。
- 轻量验证已完成：六个 skill 均通过 `skill-creator` 的 `quick_validate.py`，`python -X utf8 scripts/profile_wine_sample.py` 已成功输出样例工作簿画像。
- 本次变更未修改应用行为、数据库 schema、迁移文件或产品功能；未运行重测试。

## 2026-06-13 更新：CSV confirm 批量事务边界

- CSV 导入确认改为单个数据库事务提交：批次内任意一行在写入阶段失败时，整批 rollback，不会留下部分 bottle 或部分 `IN` transaction。
- `InventoryService` 保留默认自动提交行为，同时新增可被外层事务托管的入库结果路径，CSV confirm 复用同一套 ledger 规则且不直接修改库存快照。
- CSV confirm 成功响应新增 `created_transaction_ids`，用于追踪每个导入 bottle 对应的 `IN` ledger 记录。
- 新增后端测试覆盖成功导入的 transaction id，以及中途失败时 bottle 和 transaction 均不落库。

## 2026-06-13 更新：本地数据库迁移策略

- 新增 Alembic 迁移配置，默认继续使用 SQLite，并通过 `WINE_CELLAR_DATABASE_URL` 指向目标数据库。
- 新增初始 Alpha baseline migration，可从空数据库创建当前 schema，也可在已有当前 Alpha SQLite 库上写入 Alembic 版本记录而不删除数据。
- 新增 `scripts/backup_sqlite_db.py`，用于迁移前复制本地 SQLite 文件到 `backups/`。
- 新增迁移 smoke 测试，覆盖空库 upgrade 和已有 Alpha schema upgrade 后数据保留。
- 新增 `docs/16-database-migrations.md`，README 已补充初始化、升级、备份和本地开发库 reset 命令。

## 2026-06-13 更新：适饮期规则引擎与酒窖健康洞察

- 新增后端规则服务，基于 `Vintage.default_drink_from/default_drink_to/drink_window_confidence` 和服务器当前日期计算 `UNKNOWN`、`TOO_EARLY`、`ENTERING`、`IN_WINDOW`、`LATE`、`PAST`。
- 扩展 `/api/dashboard/summary`，保留原有统计字段，并新增适饮期细分、近期可喝候选、过期风险清单、可用/不可用瓶数、酒窖健康评分和评分因子说明。
- 前端 Dashboard 增加酒窖健康面板、适饮状态分布、近期可喝与过期风险列表；藏酒列表和详情页显示适饮状态徽标。
- 新增 `docs/15-drink-window-rules.md`，说明规则边界、状态定义、dashboard 健康分算法和非目标。
- 最新验证：后端 `pytest`、前端 `test:ui`、前端 `build`、`qa:alpha` 均已通过。

## 当前项目状态

当前处于本地 Alpha Demo 阶段。后端已具备 FastAPI + SQLite + SQLAlchemy 基础模型、Alembic migration、CRUD API、库存 transaction workflow、Dashboard、CSV 导出、安全 CSV 导入草稿、WineList Stock 真实库存导入和批量事务确认工作流，以及本地酒标图片 intake 草稿工作流。前端已具备 React + Vite Alpha UI，覆盖 Dashboard、藏酒列表、酒瓶详情、手动入库、酒标入库、酒柜地图、Transaction 历史、CSV 导出、CSV 导入草稿和 WineList Excel 导入 dry-run/确认。

项目仍保持本地单用户、无云同步、无账号权限、无真实 AI/OCR、无价格爬虫、无推荐引擎。当前酒标草稿使用本地 mock filename heuristic，只用于流程演示和字段预填。

## 已完成任务

1. 2026-06-12：建立项目规则、产品边界、数据模型、API 草案、路线图和 Codex backlog。
2. 2026-06-12：实现 FastAPI 后端骨架、健康检查、SQLite 连接和测试框架。
3. 2026-06-12：实现核心数据模型，包括 Producer、Wine、Vintage、Bottle、Cellar、Location、InventoryTransaction 等。
4. 2026-06-13：实现基础 CRUD API、库存入库和 transaction service。
5. 2026-06-13：强化库存 transaction 规则，MOVE、CONSUME、GIFT、DAMAGE、ADJUST 均保留 ledger，禁止重复出库。
6. 2026-06-13：实现 React 前端 Alpha Demo，包括 Dashboard、藏酒列表、酒瓶详情、手动入库、酒柜地图和 Transaction 历史。
7. 2026-06-13：实现 CSV 导出 `/api/export/bottles.csv`。
8. 2026-06-13：升级 Vite 相关依赖，补充 `test:ui` 和 `qa:alpha` 自动化 QA。
9. 2026-06-13：实现 CSV 导入草稿 workflow：解析 CSV、逐行校验、前端展示错误、用户确认后通过 `IN` transaction 入库。
10. 2026-06-13：新增项目跟踪文档：`docs/progress.md`、`docs/roadmap.md`、`docs/open-issues.md`。
11. 2026-06-13：实现酒标图片 intake workflow：本地上传、元数据记录、mock 草稿、前端编辑确认，并通过 `IN` ledger 入库。
12. 2026-06-13：重构前端结构，将 1616 行 `App.tsx` 拆分为 58 行 shell/routing composition，并新增 pages/components/hooks/utils/domain 模块。
13. 2026-06-13：为 CSV confirm 增加批量事务边界，成功导入返回 bottle id 和 `IN` transaction id，中途失败整批 rollback。
14. 2026-06-13：实现 WineList Stock 真实库存导入，新增 import batch 审计表、后端 draft/confirm API、前端库存导入入口和安全导入规则文档。
15. 2026-06-13：实现 Import Batch Detail / Review，新增批次 list/detail API 和前端历史审计视图。

## 本次变更涉及的主要模块

- `apps/api/app/services/winelist_import_service.py`：解析 WineList Stock、生成 draft、执行 atomic confirm，并复用 Producer/Wine/Vintage registry。
- `apps/api/app/models/import_batch.py`：新增 import batch 和 import row 审计模型。
- `apps/api/app/routers/winelist_import.py`：新增 WineList draft/confirm API。
- `apps/api/app/routers/import_batches.py`：新增导入批次只读 list/detail API。
- `apps/api/migrations/versions/20260613_0002_import_batches.py`：新增导入审计表 migration。
- `apps/api/tests/test_winelist_import.py`：覆盖真实样本 dry-run、119 瓶展开、重复导入阻止和 confirm 失败 rollback。
- `apps/web/src/pages/CsvImportPage.tsx`：新增 WineList Excel 导入 UI、Import Batch History/Detail，并保留 CSV 导入草稿。
- `docs/17-real-inventory-import.md`：新增真实库存导入规则、字段映射、位置映射和限制。

## 最新验证结果

- `python -m pytest -q`，工作目录 `apps/api`：通过，`43 passed in 10.97s`。
- `npm.cmd run test:ui`，工作目录 `apps/web`：通过，`1 passed`。
- `npm.cmd run build`，工作目录 `apps/web`：通过，Vite `8.0.16` production build 成功。
- `npm.cmd run qa:alpha`，工作目录 `apps/web`：通过，`failures: []`，包含 `importedBottles: 1`、`total_bottles: 6`、`in_stock_bottles: 2`、`health_score: 79`。

## 已知限制

- CSV 导入确认要求目标 `cellar_name + location_code` 已存在；当前不在导入时自动创建酒柜位置。
- CSV `tags` 字段当前只解析和提示，不写入标签关系表。
- 酒标草稿当前只由 mock filename heuristic 预填，不能代表真实 OCR/AI 识别。
- 酒标草稿没有持久化 draft/reject 历史；确认后只保留 upload 与 bottle 的关联。
- 已上传酒标图片暂未在 bottle detail 回看。
- 前端已完成第一轮页面/组件拆分；`CellarPage`、`AddBottlePage`、`LabelIntakePage` 仍可继续拆成更小的 feature components。
- `styles.css` 仍是单文件样式表，后续可按 layout/page/component 分段整理。
- WineList Excel 导入只支持 `Stock` sheet；不是通用 Excel 导入器，也不导入 shipment、HKStock、盲品或价格参考表。
- 没有导入批次撤销或 rollback wizard；如需撤销，应通过 ledger 补偿流程设计，不应删除原始 transaction。
- CSV 仍没有模板下载、导入历史和导入回滚。
- 没有真实 AI/OCR、价格 provider、云同步、账号权限、多用户、支付、电商、社区或推荐引擎。

## 下一步建议任务

1. 为 WineList 导入设计人工撤销/补偿流程，但保持 ledger 不可篡改，不做删除式 rollback。
2. 继续细拆 `CellarPage`、`AddBottlePage`、`LabelIntakePage` 内部表单组件，降低单页文件长度。
3. 为酒标 intake 增加持久化 draft/reject 历史和 bottle detail 图片回看。
4. 为 CSV 导入补充“下载模板 CSV”和“只显示无效行/有效行”的前端辅助操作。
5. 增加数据库恢复演练文档和示例数据隔离检查。
