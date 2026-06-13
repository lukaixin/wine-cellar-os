# 项目进度

最后更新：2026-06-13

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

当前处于本地 Alpha Demo 阶段。后端已具备 FastAPI + SQLite + SQLAlchemy 基础模型、CRUD API、库存 transaction workflow、Dashboard、CSV 导出、安全 CSV 导入草稿和批量事务确认工作流，以及本地酒标图片 intake 草稿工作流。前端已具备 React + Vite Alpha UI，覆盖 Dashboard、藏酒列表、酒瓶详情、手动入库、酒标入库、酒柜地图、Transaction 历史、CSV 导出和 CSV 导入草稿。

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

## 本次变更涉及的主要模块

- `apps/api/app/services/csv_import_service.py`：CSV confirm 统一在批次末尾提交，异常时 rollback。
- `apps/api/app/services/inventory_service.py`：入库服务新增可返回 bottle + transaction 且由外层控制 commit 的路径。
- `apps/api/app/schemas/common.py`：CSV confirm 响应新增 `created_transaction_ids`。
- `apps/api/tests/test_csv_import.py`：补充成功 ledger id 和中途失败整批回滚测试。
- `apps/web/src/types.ts`：同步 CSV confirm 响应类型。

## 最新验证结果

- `C:\Users\lukai\AppData\Local\Programs\Python\Python313\python.exe -m pytest -q`，工作目录 `apps/api`：通过，`39 passed in 8.48s`。
- `npm.cmd run test:ui`，工作目录 `apps/web`：通过，`1 passed`。
- `npm.cmd run build`，工作目录 `apps/web`：通过，Vite `8.0.16` production build 成功。
- `$env:WINE_CELLAR_PYTHON='C:\Users\lukai\AppData\Local\Programs\Python\Python313\python.exe'; npm.cmd run qa:alpha`，工作目录 `apps/web`：通过，`failures: []`，包含 `importedBottles: 1`、`total_bottles: 6`、`in_stock_bottles: 2`、`health_score: 79`。

## 已知限制

- CSV 导入确认要求目标 `cellar_name + location_code` 已存在；当前不在导入时自动创建酒柜位置。
- CSV `tags` 字段当前只解析和提示，不写入标签关系表。
- 酒标草稿当前只由 mock filename heuristic 预填，不能代表真实 OCR/AI 识别。
- 酒标草稿没有持久化 draft/reject 历史；确认后只保留 upload 与 bottle 的关联。
- 已上传酒标图片暂未在 bottle detail 回看。
- 前端已完成第一轮页面/组件拆分；`CellarPage`、`AddBottlePage`、`LabelIntakePage` 仍可继续拆成更小的 feature components。
- `styles.css` 仍是单文件样式表，后续可按 layout/page/component 分段整理。
- 没有 Excel 导入、模板下载、导入历史和导入回滚。
- 没有真实 AI/OCR、价格 provider、云同步、账号权限、多用户、支付、电商、社区或推荐引擎。

## 下一步建议任务

1. 继续细拆 `CellarPage`、`AddBottlePage`、`LabelIntakePage` 内部表单组件，降低单页文件长度。
2. 为酒标 intake 增加持久化 draft/reject 历史和 bottle detail 图片回看。
3. 为 CSV 导入补充“下载模板 CSV”和“只显示无效行/有效行”的前端辅助操作。
4. 为 CSV 导入增加 import batch 记录，追踪一次批量导入的来源、行数和结果。
5. 增加数据库恢复演练文档和示例数据隔离检查。
