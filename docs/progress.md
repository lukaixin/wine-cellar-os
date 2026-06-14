# 项目进度

最后更新：2026-06-14

## 2026-06-13 更新：Beta-1A Registry Foundation

- 不新增 `WineRegistry` 根表，继续基于 `Producer -> Wine -> Vintage` 增强主数据治理。
- Producer 新增 `canonical_key/quality_status/merged_into_id/reviewed_at`；Wine 新增 `wine_identity_key/quality_status/merged_into_id/reviewed_at`；Vintage 新增 `quality_status/reviewed_at`。
- 新增 `registry_aliases`、`import_mappings`、`registry_review_queue`、`registry_quality_findings` 表和非破坏性 Alembic migration `20260613_0003_registry_foundation.py`。
- 新增 registry 标准化服务：NFKC、trim、casefold、去重音、空格归一、标点归一；`wine_identity_key` 至少包含 producer key 和 wine name，不只依赖酒名。
- WineList draft 新增 producer/wine/vintage/overall match score 和 decision，并记录 import mapping；80-95 分、alias 冲突、缺失字段会进入 review queue。
- 新增只读 API：`GET /registry/aliases`、`GET /registry/import-mappings`、`GET /registry/review-queue`、`GET /registry/quality/findings`，并提供 `/api/registry/...` 等价路径。
- 前端新增 `Registry Quality` 页面，展示 Findings、Review Queue、Alias、Import Mapping；库存导入页同步展示 WineList 匹配分和 decision。
- 本轮不实现审批流、不自动合并、不迁移 Bottle 外键、不修改 Ledger、不删除历史数据、不增加硬唯一约束。

## 2026-06-13 更新：Beta-2 Registry Search & Discovery

- 新增统一 registry search service，按 `Producer / Wine / Vintage` 分类返回结果，字段包含 `id/entity_type/display_name/matched_text/matched_by/score/quality_status`。
- 搜索支持 canonical name、中文名、registry alias、旧 `aliases` 字段、partial 和本地 fuzzy 匹配；Vintage 搜索会继承 Wine/Producer 的 registry alias 参与发现。
- 排序规则保持 canonical exact 优先，其次 approved alias、fuzzy alias、partial；`quality_status` 较差的对象会降权。
- 新增只读 API：`GET /registry/search?q=`、`GET /registry/producers/{id}`、`GET /registry/wines/{id}`、`GET /registry/vintages/{id}`、`GET /registry/discovery`，并提供 `/api/registry/...` 等价路径。
- 前端新增 `Registry Search` 页面，支持搜索框、Producer/Wine/Vintage 分类结果、点击详情、最近新增 registry entity 和 alias/duplicate 风险 discovery。
- 本轮不实现 merge、approve/reject、推荐、AI sommelier、外部数据源、价格导入或自动合并；未修改 Bottle、Ledger、Inventory 写路径，也没有新增数据库迁移。

## 2026-06-14 更新：Beta-3A Collection Explorer MVP

- 新增只读 Collection Search API：`GET /collection/search` 和 `/api/collection/search`，支持 `q` 搜索以及 Producer、Vintage、Location、Status 四类筛选，返回 Bottle 库存分组结果并支持分页。
- 新增只读 Bottle Detail API：`GET /collection/bottles/{id}` 和 `/api/collection/bottles/{id}`，只展示 Bottle、Vintage、Wine、Producer、Quantity、Location、Acquisition Date 等基础字段。
- 前端新增 `Collection Explorer` 页面，采用左侧 filters、顶部搜索框、中间结果列表、右侧 Bottle Detail Drawer 布局。
- 本轮不实现 analytics、price、drink window、recommendation、registry governance；不修改数据库 schema，不修改 Bottle/Ledger/Inventory 写路径。

## 2026-06-14 更新：Beta-3B Bottle Detail & Timeline

- 增强只读 Bottle Detail API：`GET /collection/bottles/{id}` 和 `/api/collection/bottles/{id}` 继续保留 `id`，并新增同值 `bottle_id`，明确展示 status、quantity、producer/wine/vintage identity、location、acquisition_date 和 registry link id。
- 新增只读 Bottle Timeline API：`GET /collection/bottles/{id}/timeline` 和 `/api/collection/bottles/{id}/timeline`，按时间倒序返回来自 `inventory_transactions` 的库存事件，不新增独立历史表。
- 前端 Collection Explorer 支持 Group 展开组内 Bottle，用户点击具体 Bottle 后打开右侧 Detail Drawer，并可在 Detail / Timeline tab 间切换查看。
- Timeline UI 展示事件类型、时间、位置变化、数量变化和 notes，保持只读、可滚动，不提供任何库存写操作入口。
- 本轮不修改数据库 schema，不修改 `InventoryService` 写路径，不新增 Consume/Gift/Move/Damage/Delete/Merge，不实现 analytics 或 registry governance。

## 2026-06-14 更新：Beta-4 Inventory Actions

- 新增 action API：`POST /inventory/actions/consume|gift|damage|move`，并提供 `/api/inventory/actions/...` 等价路径。
- 四个 action 均复用 `InventoryService.apply_transaction`，先写 `InventoryTransaction` ledger，再同步 `Bottle.current_status/current_location_id` 查询快照；没有新增直接改库存状态的写路径。
- `Consume/Gift/Damage` 校验 `quantity == 1`，防止单瓶实例超额扣减；重复出库、已出库后移动、无效 location、stale from_location 均返回错误且不产生 ledger。
- `Gift.recipient` 和 `Damage.reason` 写入 transaction reason，Timeline 合并显示 reason 与 note；Timeline API 协议不变。
- Collection Explorer 的 Bottle Detail Drawer 新增 `Actions` tab，支持 Consume、Gift、Move、Damage，提交后刷新 Bottle Detail、Timeline、Collection Search 和全局 app data。
- 新增 `docs/22-inventory-actions.md`，说明 Action Types、API、Validation Rules、Timeline Integration 和迁移策略。

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

当前处于本地 Alpha Demo + Beta inventory actions 阶段。后端已具备 FastAPI + SQLite + SQLAlchemy 基础模型、Alembic migration、CRUD API、库存 transaction workflow、Dashboard、CSV 导出、安全 CSV 导入草稿、WineList Stock 真实库存导入和批量事务确认工作流、Registry Foundation 观察表、质量发现、统一 registry search/detail/discovery API、Collection search/detail/timeline API、Inventory Actions API，以及本地酒标图片 intake 草稿工作流。前端已具备 React + Vite Alpha UI，覆盖 Dashboard、藏酒列表、Collection Explorer、Bottle Detail Drawer Actions/Timeline、手动入库、酒标入库、酒柜地图、Transaction 历史、CSV 导出、CSV 导入草稿、WineList Excel 导入 dry-run/确认、Registry Quality 和 Registry Search 页面。

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
16. 2026-06-13：实现 Beta-1A Registry Foundation，新增 canonical key、alias/mapping/review/finding 表、WineList 匹配分、Registry Quality 页面和增量 migration。
17. 2026-06-13：实现 Beta-2 Registry Search & Discovery，新增统一 registry 搜索服务、只读详情 API、discovery API、Registry Search 页面和搜索/详情测试。
18. 2026-06-14：实现 Beta-3A Collection Explorer MVP，新增 collection search/detail API、Collection Explorer 页面、API/UI 测试和 `docs/20-collection-explorer.md`。
19. 2026-06-14：实现 Beta-3B Bottle Detail & Timeline，新增 collection bottle timeline API、组内 Bottle 展开、Detail/Timeline tab、API/UI 测试和 `docs/21-bottle-detail-timeline.md`。
20. 2026-06-14：实现 Beta-4 Inventory Actions，新增 ledger-backed Consume/Gift/Move/Damage action API、Bottle Detail Drawer Actions tab、API/UI 测试和 `docs/22-inventory-actions.md`。

## 本次变更涉及的主要模块

- `apps/api/app/services/winelist_import_service.py`：解析 WineList Stock、生成 draft、执行 atomic confirm，并复用 Producer/Wine/Vintage registry。
- `apps/api/app/services/registry_service.py`：生成 canonical key / wine identity key，记录 import mapping，维护 alias 冲突和 review queue，生成质量 findings，并提供统一 registry search/detail/discovery 读服务。
- `apps/api/app/services/collection_service.py`：提供只读 Collection Search 和 Bottle Detail 查询，按库存 Bottle 维度聚合结果。
- `apps/api/app/services/collection_service.py`：新增只读 Bottle Timeline 查询，直接读取 `InventoryTransaction` ledger 并按时间倒序返回事件。
- `apps/api/app/routers/inventory_actions.py`：新增 Consume/Gift/Damage/Move action API，复用 `InventoryService` ledger 规则并返回 transaction。
- `apps/api/app/schemas/common.py`：新增 action request schema，包含单瓶 quantity、recipient、reason 和 from/to location payload。
- `apps/api/app/models/registry.py`：新增 registry alias、import mapping、review queue、quality finding 模型。
- `apps/api/app/routers/registry.py`：新增 registry 只读 API，包括 search、detail、discovery、alias、mapping、review queue 和 quality findings。
- `apps/api/app/routers/collection.py`：新增 collection search/detail 只读 API。
- `apps/api/app/routers/collection.py`：新增 collection bottle timeline 只读 API，含 `/collection/...` 和 `/api/collection/...` 两套路由。
- `apps/api/app/models/import_batch.py`：新增 import batch 和 import row 审计模型。
- `apps/api/app/routers/winelist_import.py`：新增 WineList draft/confirm API。
- `apps/api/app/routers/import_batches.py`：新增导入批次只读 list/detail API。
- `apps/api/migrations/versions/20260613_0002_import_batches.py`：新增导入审计表 migration。
- `apps/api/migrations/versions/20260613_0003_registry_foundation.py`：新增 registry foundation migration，回填 Producer/Wine key。
- `apps/api/tests/test_winelist_import.py`：覆盖真实样本 dry-run、119 瓶展开、重复导入阻止和 confirm 失败 rollback。
- `apps/api/tests/test_registry_foundation.py`：覆盖 canonical key、alias conflict、mapping、review queue、quality findings 和 WineList score。
- `apps/api/tests/test_registry_foundation.py`：新增 registry search、alias search、ranking、detail API 和 discovery API 覆盖。
- `apps/api/tests/test_collection_explorer.py`：覆盖 collection search、filters、pagination 和 bottle detail。
- `apps/api/tests/test_collection_explorer.py`：新增 bottle timeline、timeline ordering、empty timeline 和 missing bottle 覆盖。
- `apps/api/tests/test_inventory_actions.py`：新增 Consume/Gift/Damage/Move action API、quantity、重复出库、stale location 和 ledger 不变量覆盖。
- `apps/web/src/pages/CsvImportPage.tsx`：新增 WineList Excel 导入 UI、Import Batch History/Detail，并保留 CSV 导入草稿。
- `apps/web/src/pages/RegistryQualityPage.tsx`：新增 Registry Quality 页面。
- `apps/web/src/pages/RegistrySearchPage.tsx`：新增 Registry Search 页面，分类展示搜索结果、详情和 discovery。
- `apps/web/src/pages/CollectionExplorerPage.tsx`：新增 Collection Explorer 页面，支持搜索、筛选、分页和详情抽屉。
- `apps/web/src/pages/CollectionExplorerPage.tsx`：新增 group 展开、组内 Bottle 选择和 Detail/Timeline tab 展示。
- `apps/web/src/pages/CollectionExplorerPage.tsx`：新增 Bottle Detail Drawer Actions tab，提交 action 后刷新 detail、timeline、collection search 和全局数据。
- `docs/17-real-inventory-import.md`：新增真实库存导入规则、字段映射、位置映射和限制。
- `docs/18-registry-foundation.md`：新增 registry foundation schema、API、migration 和限制说明。
- `docs/19-registry-search.md`：新增 registry search/discovery 设计、API、排序和限制说明。
- `docs/20-collection-explorer.md`：新增 collection explorer API、页面说明、数据流和限制说明。
- `docs/21-bottle-detail-timeline.md`：新增 Bottle Detail、Timeline API、UI Flow 和 Known Limitations 说明。
- `docs/22-inventory-actions.md`：新增 Inventory Actions API、校验规则、Timeline 集成和非目标说明。

## 最新验证结果

- `python -m pytest -q`，工作目录 `apps/api`：通过，`59 passed in 21.93s`。
- `npm.cmd run build`，工作目录 `apps/web`：通过，Vite `8.0.16` production build 成功。
- `npm.cmd run test:ui`，工作目录 `apps/web`：通过，`1 passed`。
- `npm.cmd run qa:alpha`，工作目录 `apps/web`：通过，`failures: []`，包含 `importedBottles: 1`、`total_bottles: 6`、`in_stock_bottles: 2`、`health_score: 79`。
- 截图验证：生成 `artifacts/beta-3b-bottle-detail-timeline.png`，覆盖 Collection Explorer group 展开、Bottle 选择和 Timeline tab。

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
- Registry Review Queue 当前只读展示，不实现审批流或 approve/reject 操作。
- Alias Registry 当前提供模型、内部记录和只读 API；人工 alias 管理 UI 留待后续。
- Registry Search 当前是本地规则搜索，不使用外部数据源；fuzzy 匹配基于本地字符串相似度，不代表权威酒款数据库。
- Registry Discovery 的 new producers/wines/vintages 基于本地 `created_at`，不区分手工创建和导入创建。
- `merged_into_id` 只是治理标记，不会自动迁移 Bottle 外键或改写 Ledger。
- CSV 仍没有模板下载、导入历史和导入回滚。
- 没有真实 AI/OCR、价格 provider、云同步、账号权限、多用户、支付、电商、社区或推荐引擎。

## 下一步建议任务

1. 为 Registry Review Queue 增加人工处理状态、alias approve/reject 和 merge planning，但不要自动改写 Bottle/Ledger。
2. 为 WineList 导入设计人工撤销/补偿流程，但保持 ledger 不可篡改，不做删除式 rollback。
3. 为 Registry Search 增加高亮匹配片段、筛选质量状态和更明确的 alias provenance。
4. 继续细拆 `CellarPage`、`AddBottlePage`、`LabelIntakePage` 内部表单组件，降低单页文件长度。
5. 为酒标 intake 增加持久化 draft/reject 历史和 bottle detail 图片回看。
6. 为 CSV 导入补充“下载模板 CSV”和“只显示无效行/有效行”的前端辅助操作。
7. 增加数据库恢复演练文档和示例数据隔离检查。
