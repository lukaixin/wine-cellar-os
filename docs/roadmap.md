# 项目路线图

最后更新：2026-06-13

## 2026-06-13 数据库迁移状态

本地 Alpha 已引入 Alembic 迁移策略。当前 baseline migration 支持空 SQLite 建库，也支持已有当前 Alpha schema 写入版本记录而不删除数据。近期路线中的“Alpha 数据向 Beta 演进”技术前置条件已部分完成；后续新增字段/表时应优先写增量 migration，而不是要求用户重建数据库。

## 2026-06-13 CSV 导入事务状态

CSV confirm 已从逐行提交改为单批次事务提交。成功导入仍通过 `IN` ledger 创建每瓶库存；任意一行在写入阶段失败会整批 rollback。近期 CSV import 的剩余重点转为模板下载、导入预览筛选、标签落库和 import batch 历史。

## 2026-06-13 适饮期与健康洞察状态

Phase 3 中的“适饮期”已从字段展示推进到规则化洞察：后端会按服务器当前年份计算适饮状态，Dashboard 会展示近期可喝、过期风险和透明的酒窖健康评分。价格快照、资产视图、估值趋势仍未实现，后续仍按 manual/csv/screenshot/link note provider 的合规边界推进。

本文件是当前执行视角的路线图。原始阶段规划仍保留在 `docs/08-roadmap.md`。

## 当前阶段

当前处于 `v0.4-local-alpha-demo`，重点是把本地酒窖管理闭环做稳：模型、库存 ledger、酒柜位置、基础前端、导出、安全导入草稿和酒标本地 intake 草稿。

## 阶段进度

| 阶段 | 状态 | 说明 |
| --- | --- | --- |
| Phase 0 文档和规则 | 已完成 | 已建立 README、AGENTS、PRD、数据模型、API 草案、backlog、ADR。 |
| Phase 1 本地库存核心 | 已完成 | 后端模型、CRUD、库存 transaction service、审计规则和测试已建立。 |
| Phase 2 前端 MVP | 已完成 Alpha | Dashboard、藏酒列表、详情、手动入库、酒柜地图、Transaction 历史已可用。 |
| Phase 3 适饮与资产 | 部分完成 | 已有适饮期字段和 Dashboard 计数；价格快照、资产视图仍未实现。 |
| Phase 4 导入导出和备份 | 进行中 | CSV 导出已完成；CSV 导入草稿、批量事务确认和基础数据库迁移/备份命令已完成；Excel、恢复演练、import batch 历史未实现。 |
| Phase 5 AI 辅助录入 | 壳子已完成 | 已有本地酒标上传、mock 草稿和人工确认入库；真实 AI/OCR 仍未开始，未来也只能生成草稿，不能直接改库存。 |
| Phase 6 建议引擎 | 未开始 | 当前不做采购建议、推荐或预测。 |
| Phase 7 推广准备 | 未开始 | 当前无云同步、账号权限、多用户或商业化设计。 |

## 近期路线

1. 稳定 CSV import：模板下载、导入预览筛选、标签落库、import batch 历史。
2. 补齐本地数据安全：数据库恢复演练、示例数据和真实数据隔离。
3. 进入资产/价格基础能力：只做 manual/csv/screenshot/link note provider，不做受限网站抓取。
4. 继续细拆前端较大的 page/form 组件，并补更细的 UI smoke，降低维护风险。
5. 为酒标 intake 增加 draft/reject 历史和详情页图片回看。
6. 为下一次模型变更建立增量 migration 编写和验证流程。

## 明确不进入近期路线的事项

- 真实 AI 酒标识别和 OCR。
- Wine-Searcher 或其他受限网站 scraping。
- 云同步、账号系统、权限、多用户。
- 推荐引擎、采购建议、自动购买链接。
- 电商、社区、评分平台。
