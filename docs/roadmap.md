# 项目路线图

最后更新：2026-06-14

## 2026-06-14 Beta-6 Safety Foundation 状态

Beta-6 Safety Foundation 已完成 Import Compensation 与 Backup & Restore。WineList import batch 现在支持 ledger-safe compensation：通过 `ADJUST` transaction 抵消批次影响，保留原始 `IN` ledger、batch rows 和 timeline 历史。Safety Admin 现在支持本地 SQLite 备份、备份列表、typed-confirmation restore、pre-restore backup 和 `safety_events` 审计记录。

Beta-6 已完成能力：

- Import Compensation：按 WineList batch 生成可审计补偿交易，拒绝重复补偿和已发生后续库存活动的 bottle。
- Backup：创建不覆盖旧文件的 timestamped SQLite backup，并记录 `BACKUP_CREATED`。
- Restore：校验 backup path、SQLite `quick_check`、Alembic version 与 typed confirmation，恢复前创建 pre-restore backup，并记录 `RESTORE_COMPLETED`。

Beta-6 不包含：Registry governance、AI/OCR、Valuation、价格 provider、云同步、权限系统、多用户或自动采购建议。

## 2026-06-14 Beta-5 RC1 Release Freeze 状态

Beta-5 已完成 RC1 Release Freeze。Release gates 已通过 Automated Tests、Critical UAT、Ledger Validation、WS Price Validation 和 Demo Dataset Validation。当前结论：Beta-5 具备本地单用户 Release Candidate 资格，可用于演示、UAT 回归、版本管理和 Beta-6 计划输入。

RC1 稳定能力：

- Import：CSV draft/confirm、WineList Stock draft/confirm、Import Batch Review、WS Price 导入。
- Registry：Foundation、Quality、Search、Discovery 的只读/观察能力。
- Collection：search、filters、pagination、Bottle Detail。
- Timeline：基于 `InventoryTransaction` 的 Import/Move/Consume/Gift/Damage history。
- Inventory Actions：Consume、Gift、Move、Damage，均复用 ledger-backed `InventoryService`。
- Analytics：只读 Inventory Overview、Consumption、Activity、WS Price 汇总。

RC1 不包含：导入补偿 wizard、Registry approve/reject/merge、真实 AI/OCR、价格 provider、估值历史、ROI、推荐、云同步、账号权限或多用户。

## 2026-06-13 Registry Foundation 状态

Beta-1A 已完成主数据治理基础层：不新增 `WineRegistry` 根表，继续使用 `Producer -> Wine -> Vintage`，并新增 canonical key、wine identity key、alias registry、import mapping、review queue 和 quality findings。WineList draft 已输出匹配分和 decision；前端新增 Registry Quality 页面。当前 Beta 进度约 62%-65%，Vision 仍保持 35%。

## 2026-06-14 Beta-5 Analytics Foundation + WS Price Import Extension 状态

Beta-5 已完成基础分析层和 WineList `WS Price` 导入扩展，并已冻结为 RC1：新增只读 Analytics API/UI，展示库存 summary、Country/Region/Vintage/Status 分布、Consumption periods、Monthly Trend 和 Recent Activity；Consumption 与 Activity 直接来自 `InventoryTransaction` ledger。Bottle 新增 nullable `ws_price` 字段，WineList Stock draft/confirm 支持 `WS Price`，Bottle Detail 和 Collection Bottle Detail 返回 `ws_price`，Analytics 展示 `total_ws_value = SUM(ws_price)`。本轮不包含 ROI、价格历史、估值模型、价格/消费预测、AI 推荐或治理审批。当前 Beta-5 状态为 RC1 frozen；Vision 仍保持 35%。

## 2026-06-13 Registry Search 状态

Beta-2 已完成 Registry Search & Discovery：统一搜索服务支持 Producer/Wine/Vintage 分类结果，覆盖 canonical name、中文名、approved alias、旧 aliases、partial 和本地 fuzzy 匹配；新增只读详情 API 和 discovery API；前端新增 Registry Search 页面。当前 Beta 进度约 72%-75%，Vision 仍保持 35%。

## 2026-06-14 Collection Explorer 状态

Beta-3A 已完成 Collection Explorer MVP：新增只读 collection search/detail API，支持 Producer、Vintage、Location、Status 四类筛选和分页；前端新增 Collection Explorer 页面，按库存 Bottle 分组展示 Producer、Wine、Vintage、Bottle Count、Location、Status，并提供右侧 Bottle Detail Drawer。当前 Beta 进度约 78%-80%，Vision 仍保持 35%。

## 2026-06-14 Bottle Detail & Timeline 状态

Beta-3B 已完成 Bottle Detail & Timeline：Collection Explorer 结果可展开组内 Bottle，点击具体 Bottle 后在右侧 Drawer 查看只读 Detail 和来自 Inventory Transaction Ledger 的 Timeline；新增 `/collection/bottles/{id}/timeline` 与 `/api/collection/bottles/{id}/timeline`。本轮未新增 schema、未修改库存写路径、未引入分析或治理能力。当前 Beta 进度约 82%-85%，Vision 仍保持 35%。

## 2026-06-14 Inventory Actions 状态

Beta-4 已完成 Inventory Actions：Bottle Detail Drawer 新增 Actions tab，支持 Consume、Gift、Move、Damage；新增 `/inventory/actions/...` 和 `/api/inventory/actions/...` action API。所有动作复用 `InventoryService` 写入 `InventoryTransaction` ledger，并同步 Bottle 查询快照；Timeline API 协议不变，自动展示新增事件。本轮不实现 analytics、valuation、drink window、recommendation 或 registry governance。当前 Beta 进度约 88%-90%，Vision 仍保持 35%。

## 2026-06-13 数据库迁移状态

本地 Alpha 已引入 Alembic 迁移策略。当前 baseline migration 支持空 SQLite 建库，也支持已有当前 Alpha schema 写入版本记录而不删除数据。Registry Foundation 已新增 `20260613_0003_registry_foundation.py`，采用非破坏性新增字段/表和 key 回填。后续新增字段/表仍应优先写增量 migration，而不是要求用户重建数据库。

## 2026-06-13 CSV 导入事务状态

CSV confirm 已从逐行提交改为单批次事务提交。成功导入仍通过 `IN` ledger 创建每瓶库存；任意一行在写入阶段失败会整批 rollback。近期 CSV import 的剩余重点转为模板下载、导入预览筛选、标签落库和 import batch 历史。

## 2026-06-13 WineList 真实库存导入状态

`data/sample/WineList.xlsx` 的 `Stock` sheet 已接入真实库存导入：draft 阶段写入 import batch 审计记录但不创建库存，confirm 阶段通过 `InventoryService` 和 `IN` ledger 原子展开 119 瓶。Import Batch Review 已支持批次列表、批次详情、行级 warning/error、created bottle ids 和 ledger transaction ids。现有 `Producer -> Wine -> Vintage` 作为第一版 Wine Registry，不引入大型 catalog；draft 现在还会记录 registry import mapping、匹配分和 review queue。其他 sheet、通用 Excel 模板和估值导入仍不在当前范围。

## 2026-06-13 适饮期与健康洞察状态

Phase 3 中的“适饮期”已从字段展示推进到规则化洞察：后端会按服务器当前年份计算适饮状态，Dashboard 会展示近期可喝、过期风险和透明的酒窖健康评分。价格快照、资产视图、估值趋势仍未实现，后续仍按 manual/csv/screenshot/link note provider 的合规边界推进。

本文件是当前执行视角的路线图。原始阶段规划仍保留在 `docs/08-roadmap.md`。

## 当前阶段

当前处于 `Beta-6 Safety Foundation`，重点是增强真实使用前的数据安全能力：模型、库存 ledger、酒柜位置、基础前端、导出、安全导入草稿、WineList 真实库存导入、Import Compensation、Registry Search/Discovery、Collection Explorer、Bottle Timeline、Inventory Actions、Analytics Foundation、WS Price Import Extension、官方 demo dataset 和 Backup & Restore。

## 阶段进度

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| Phase 0 文档和规则 | 已完成 | 已建立 README、AGENTS、PRD、数据模型、API 草案、backlog、ADR。 |
| Phase 1 本地库存核心 | 已完成 | 后端模型、CRUD、库存 transaction service、审计规则和测试已建立。 |
| Phase 2 前端 MVP | 已完成 Alpha | Dashboard、藏酒列表、详情、手动入库、酒柜地图、Transaction 历史已可用。 |
| Phase 3 适饮与资产 | 部分完成 | 已有适饮期字段和 Dashboard 计数；价格快照、资产视图仍未实现。 |
| Phase 4 导入导出和备份 | 进行中 | CSV 导出已完成；CSV 导入草稿、WineList Stock 导入、Import Batch Review、WineList Import Compensation、批量事务确认、基础数据库迁移、Safety Admin 备份恢复和 registry mapping 观察已完成；通用 Excel、CSV 批次化补偿和自动备份策略未实现。 |
| Beta-1A Registry Foundation | 已完成基础层 | Canonical key、alias/mapping/review/finding 表、WineList score 和 Registry Quality 页面已完成；不包含审批流、自动合并或 Bottle 外键迁移。 |
| Beta-2 Registry Search & Discovery | 已完成搜索层 | Registry search/detail/discovery API 和前端 Registry Search 页面已完成；不包含 merge workflow、approve/reject、推荐、外部数据源或价格导入。 |
| Beta-3A Collection Explorer MVP | 已完成库存查找层 | Collection search/detail API 和 Collection Explorer 页面已完成；不包含 analytics、price、drink window、recommendation 或 registry governance。 |
| Beta-3B Bottle Detail & Timeline | 已完成单瓶链路 | Group 展开组内 Bottle、Bottle Detail Drawer tab 和 ledger timeline API/UI 已完成；不包含任何库存写操作。 |
| Beta-4 Inventory Actions | 已完成库存操作层 | Bottle Detail Drawer Actions tab 和 Consume/Gift/Move/Damage action API 已完成；所有写操作 ledger-backed，不包含 analytics、估值、推荐或 registry governance。 |
| Beta-5 Analytics Foundation | RC1 frozen | Analytics API/UI、ledger-backed consumption/activity、WineList WS Price 导入和 Bottle `ws_price` 已完成；Release Review、Release Notes 和 Demo Dataset 已生成；不包含 ROI、价格历史、预测、AI 或治理审批。 |
| Beta-6 Safety Foundation | 已完成安全基础层 | WineList batch compensation、SQLite backup/list/restore、pre-restore backup、Safety Admin 和 `safety_events` 已完成；不包含 Governance、AI、Valuation、云同步或权限系统。 |
| Phase 5 AI 辅助录入 | 壳子已完成 | 已有本地酒标上传、mock 草稿和人工确认入库；真实 AI/OCR 仍未开始，未来也只能生成草稿，不能直接改库存。 |
| Phase 6 建议引擎 | 未开始 | 当前不做采购建议、推荐或预测。 |
| Phase 7 推广准备 | 未开始 | 当前无云同步、账号权限、多用户或商业化设计。 |

## 推荐 Beta-6C 路线

1. 扩展 CSV import batch 审计与补偿，让 CSV 也复用 WineList 的 batch history 和 ledger-safe compensation 模式。
2. 固化 demo dataset 生成脚本，确保 demo workbook 和 demo database 可重复生成且不混入真实数据。
3. 为 Backup & Restore 增加恢复演练 checklist、备份保留策略和真实数据隔离检查，但仍保持本地优先。
4. 稳定 Registry Review Queue：人工处理状态、alias approve/reject、merge planning，但不自动迁移 Bottle 或改写 Ledger。
5. 优化 Registry Search：匹配高亮、质量状态筛选、alias provenance 展示和更细的 fuzzy 阈值校准。
6. 继续细拆前端较大的 page/form 组件，并补更细的 UI smoke，降低维护风险。
7. 为酒标 intake 增加 draft/reject 历史和详情页图片回看。

## 推荐 V1 边界

V1 建议继续保持本地单用户和可审计库存为核心：

- 稳定本地库存、导入导出、ledger、Collection、Timeline、Inventory Actions 和基础 Analytics。
- 提供可恢复、可迁移、可演示的数据包和备份/恢复流程。
- 建立 Registry governance 的人工确认闭环，但不自动改写历史 ledger。
- 价格层先做 manual/csv/screenshot/link note provider 和 valuation snapshot，不做受限网站抓取。
- AI/OCR 只作为草稿生成器，正式库存仍必须用户确认。

不建议 V1 纳入云同步、账号权限、多用户、电商、社区、推荐引擎或自动购买链路，除非重新定义产品范围。

## 明确不进入近期路线的事项

- 真实 AI 酒标识别和 OCR。
- Wine-Searcher 或其他受限网站 scraping。
- 云同步、账号系统、权限、多用户。
- 推荐引擎、采购建议、自动购买链接。
- 电商、社区、评分平台。
