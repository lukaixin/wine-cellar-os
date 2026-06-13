# Open Issues

最后更新：2026-06-13

## 2026-06-13 新增说明

- Dashboard 酒窖健康分已经可用，但只基于本地库存、位置容量和手工适饮期字段计算；它不能替代专业品鉴、储存检查、价格估值或投资建议。

## 确认 Bug

| 优先级 | 问题 | 状态 | 建议处理 |
| --- | --- | --- | --- |
| P2 | 从仓库根目录直接运行 `python -m pytest -q` 会因为 `app` import path 找不到而失败。 | 已确认 | 在 README 中保持 `apps/api` 工作目录说明；后续可增加根目录测试脚本或统一 workspace test runner。 |

当前没有已确认的库存 ledger 破坏性 bug。

## 技术债

| 优先级 | 问题 | 风险 | 建议处理 |
| --- | --- | --- | --- |
| P1 | CSV confirm 复用现有入库服务逐行提交，虽然有预检，但不是全局事务。 | 未来复杂导入出现异常时可能部分提交。 | 增加 batch import transaction boundary，或让 InventoryService 支持外层事务控制。 |
| P1 | 没有数据库迁移工具。 | 模型变更时本地 Alpha 数据升级成本高。 | 引入 Alembic 或明确本地迁移脚本策略。 |
| P2 | 前端部分 page 文件仍较大，尤其 `CellarPage`、`AddBottlePage`、`LabelIntakePage`。 | 后续继续扩展表单和交互时维护成本仍会上升。 | 继续拆分 feature components/forms，并保持现有 smoke test。 |
| P3 | 前端 `styles.css` 仍是单文件样式表。 | 样式增长后难以定位页面/组件归属。 | 后续按 layout、page、component 分段或拆分样式文件。 |
| P2 | API 测试 fixture 在多个测试文件中重复。 | 测试维护成本上升。 | 提取到 `tests/conftest.py`。 |
| P2 | CSV tags 只解析不落库。 | 用户可能以为标签已经保存。 | 接入 `tags/object_tags` 或在 UI 中更明确标注。 |
| P2 | 酒标草稿没有持久化 draft/reject 历史。 | 用户关闭页面后只能重新上传并生成草稿。 | 增加 label draft 表或 intake session 表，仍保持确认前不落正式库存。 |
| P3 | 已上传酒标图片没有详情页回看。 | 确认后用户不能从 bottle detail 查看已归档图片。 | 增加受控本地静态文件读取或 media asset 关联。 |

## 产品限制

| 优先级 | 限制 | 影响 | 建议处理 |
| --- | --- | --- | --- |
| P1 | CSV 导入要求目标酒柜和位置已存在。 | 初次迁移数据前需要先建酒柜位置。 | 增加模板和预检查清单；是否自动创建位置需另行确认。 |
| P2 | 不支持 Excel 导入。 | 用户常见库存表可能需要先另存为 CSV。 | 后续增加 xlsx 解析草稿，仍保持确认前不落库。 |
| P2 | 没有导入历史和回滚。 | 用户难以追踪一次批量导入的来源。 | 增加 import batch 记录，但不能替代库存 ledger。 |
| P2 | 酒标识别当前只是 mock filename heuristic。 | 只能作为流程演示，不能代表真实识别能力。 | 后续按 `docs/14-label-intake-ai-adapter.md` 接入本地 OCR/AI adapter。 |
| P2 | 当前价格、适饮期、产区和类型都来自人工录入或 CSV 字段。 | 不代表权威数据。 | 保留来源、置信度和 manual 标记。 |
| P3 | 没有拖拽式酒柜移动。 | 移动效率有限。 | 等 ledger 和位置规则稳定后再做拖拽。 |

## 风险

| 优先级 | 风险 | 建议处理 |
| --- | --- | --- |
| P1 | 真实库存数据库或真实购买记录被误提交。 | 保持 `.gitignore`，不要提交 `data/`、真实图片和本地数据库；文档持续提醒。 |
| P1 | 未来导入或价格模块绕过 ledger 直接改库存快照。 | 所有库存变更必须经过 InventoryService 和 InventoryTransaction 测试。 |
| P2 | 导入字段含糊导致重复 Producer/Wine/Vintage。 | 增加导入前匹配预览和人工合并流程。 |
| P2 | 价格数据来源合规风险。 | 只做 manual/csv/screenshot/link note provider，不实现反爬或批量抓取。 |
| P3 | 前端 smoke 基于 jsdom，不能覆盖真实浏览器布局。 | 关键布局稳定后补 Playwright 或浏览器截图 QA。 |
