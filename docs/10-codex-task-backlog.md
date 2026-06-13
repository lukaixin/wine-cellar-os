# Codex 任务拆分

每个任务应独立完成、独立验证，不要跨阶段扩展。

## Task 001：初始化后端项目骨架

目标：建立 `apps/api` 后端工程。

范围：

- FastAPI 应用入口。
- 配置读取。
- SQLite 连接。
- 基础健康检查 endpoint。
- 测试框架。

验收：

- `GET /health` 返回 ok。
- 本地能启动 API。
- 有最小测试。

建议提示词：见 `prompts/codex/01-implement-database-schema.md`。

## Task 002：实现数据库模型

目标：按 `docs/04-data-model.md` 创建核心模型。

范围：

- producers
- wines
- vintages
- cellars
- locations
- bottles
- inventory_transactions
- valuation_snapshots
- drink_windows
- media_assets
- tags
- object_tags

验收：

- 能创建数据库。
- 外键正确。
- 基础约束存在。
- 有模型创建测试。

## Task 003：实现库存服务

目标：所有库存变化通过 `InventoryService`。

范围：

- create_bottle_with_purchase_in
- move_bottle
- drink_bottle
- gift_bottle
- sell_bottle
- mark_damaged
- stocktake_adjustment

验收：

- 每个方法都生成 transaction。
- bottle 当前状态正确变化。
- 禁止非法状态转移。
- 有服务层测试。

## Task 004：实现基础 API

目标：提供 Producer/Wine/Vintage/Bottle/Cellar/Location CRUD。

范围：

- REST endpoint。
- Pydantic schema。
- 错误处理。
- 分页。
- 简单搜索。

验收：

- API 文档可访问。
- CRUD 测试通过。

## Task 005：初始化前端项目

目标：建立 `apps/web`。

范围：

- 前端框架初始化。
- API client。
- 页面路由。
- 基础布局。

验收：

- 可本地启动。
- 能调用 `/health`。

## Task 006：藏酒列表和详情页

目标：用户能查看库存。

范围：

- bottle 列表。
- 筛选。
- 详情页。
- 状态展示。
- 位置展示。

验收：

- 能查看、搜索、进入详情。

## Task 007：入库表单

目标：用户能手动入库。

范围：

- producer/wine/vintage/bottle 表单。
- 购买信息。
- 位置选择。
- 保存后创建 transaction。

验收：

- 新瓶入库后列表可见。
- transaction 存在。

## Task 008：酒柜二维地图

目标：可视化酒柜位置。

范围：

- 多酒柜选择。
- 行列格子。
- 空位/占用显示。
- 点击格子查看瓶。

验收：

- 能看清每个位置放了什么。

## Task 009：出库和移动操作

目标：用户能喝掉、送礼、移动。

范围：

- 操作按钮。
- 确认弹窗。
- 备注。
- transaction 记录。

验收：

- UI 与数据库状态一致。

## Task 010：Dashboard MVP

目标：首页显示酒窖状态。

范围：

- 总瓶数。
- 酒柜占用率。
- 购买成本。
- 当前估值。
- 适饮提醒。
- 过峰风险。

验收：

- 指标来自真实数据，不写死。

## Task 011：导入导出

目标：数据可迁移。

范围：

- CSV 导入。
- CSV 导出。
- 错误报告。

验收：

- 示例 CSV 可导入。
- 导出后可重新导入。

## Task 012：AI 酒标识别 draft

目标：降低录入成本，但不自动入库。

范围：

- 图片上传。
- 生成识别草稿。
- 用户确认。
- 保存识别来源和置信度。

验收：

- AI 结果不会直接改变库存。
