# Open Issues

最后更新：2026-06-13

## 2026-06-13 新增说明

- 本地数据库迁移已引入 Alembic baseline。剩余风险从“没有迁移工具”转为“旧库 schema 若偏离当前模型，需要专门增量 migration，不应靠删除数据库解决”。
- CSV confirm 已改为单批次事务提交。剩余导入风险转为“CSV 尚未复用 import batch 历史，且没有人工回滚/撤销流程”，库存 ledger 本身仍保留每瓶 `IN` transaction。
- WineList Stock 真实库存导入已新增 import batch 审计表、atomic confirm 和批次详情 review。剩余风险转为“人工撤销/补偿和更细的人工匹配确认尚未实现”。
- Dashboard 酒窖健康分已经可用，但只基于本地库存、位置容量和手工适饮期字段计算；它不能替代专业品鉴、储存检查、价格估值或投资建议。

## 确认 Bug

| 优先级 | 问题 | 状态 | 建议处理 |
| --- | --- | --- | --- |
| P2 | 从仓库根目录直接运行 `python -m pytest -q` 会因为 `app` import path 找不到而失败。 | 已确认 | 在 README 中保持 `apps/api` 工作目录说明；后续可增加根目录测试脚本或统一 workspace test runner。 |

当前没有已确认的库存 ledger 破坏性 bug。

## 技术债

| 优先级 | 问题 | 风险 | 建议处理 |
| --- | --- | --- | --- |
| P1 | Alembic baseline 已有，但历史偏离 schema 的旧库仍需要专门增量迁移。 | 用户如果跳过备份或直接删除数据库，仍可能丢失 Alpha 数据。 | 后续每次模型变更都必须新增 migration，并在升级前运行 SQLite 备份脚本。 |
| P2 | 前端部分 page 文件仍较大，尤其 `CellarPage`、`AddBottlePage`、`LabelIntakePage`。 | 后续继续扩展表单和交互时维护成本仍会上升。 | 继续拆分 feature components/forms，并保持现有 smoke test。 |
| P3 | 前端 `styles.css` 仍是单文件样式表。 | 样式增长后难以定位页面/组件归属。 | 后续按 layout、page、component 分段或拆分样式文件。 |
| P2 | API 测试 fixture 在多个测试文件中重复。 | 测试维护成本上升。 | 提取到 `tests/conftest.py`。 |
| P2 | CSV tags 只解析不落库。 | 用户可能以为标签已经保存。 | 接入 `tags/object_tags` 或在 UI 中更明确标注。 |
| P2 | WineList import batch 已可查看详情，但没有撤销/补偿向导。 | 用户可以审计来源和创建结果，但不能按批次生成安全补偿动作。 | 撤销只能通过 ledger 补偿交易设计，不应删除原 transaction。 |
| P2 | 酒标草稿没有持久化 draft/reject 历史。 | 用户关闭页面后只能重新上传并生成草稿。 | 增加 label draft 表或 intake session 表，仍保持确认前不落正式库存。 |
| P3 | 已上传酒标图片没有详情页回看。 | 确认后用户不能从 bottle detail 查看已归档图片。 | 增加受控本地静态文件读取或 media asset 关联。 |

## 产品限制

| 优先级 | 限制 | 影响 | 建议处理 |
| --- | --- | --- | --- |
| P1 | CSV 导入要求目标酒柜和位置已存在。 | 初次迁移数据前需要先建酒柜位置。 | 增加模板和预检查清单；是否自动创建位置需另行确认。 |
| P2 | CSV 导入没有 import batch 历史和人工撤销流程。 | 用户难以按批次追踪来源文件、导入行数和后续修正。 | 可复用 WineList import batch 审计模式；撤销应通过 ledger 补偿交易而不是删除原始交易。 |
| P2 | Excel 导入只支持 `WineList.xlsx` 的 `Stock` sheet。 | 其他 sheet、其他 Excel 模板和通用 xlsx 库存表仍不能直接导入。 | 后续先做模板化映射和人工字段匹配，不做自动推断或外部数据补全。 |
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
