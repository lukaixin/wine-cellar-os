# Open Issues

最后更新：2026-06-14

## 2026-06-14 Beta-6 Safety Foundation 说明

- WineList import batch compensation 已实现。当前可对未被后续库存动作触碰的 confirmed WineList batch 生成 `ADJUST` 补偿交易，原始 `IN` ledger 保留。
- Safety Admin Backup & Restore 已实现。当前支持文件型 SQLite backup/list/restore、typed confirmation、pre-restore backup、SQLite quick check、Alembic version 校验和 safety event 记录。
- 当前没有已确认的库存 ledger 破坏性 bug；新增补偿测试、备份恢复测试、迁移测试和 UI smoke 均已通过。
- 剩余问题的处理顺序建议转入 Beta-6C：CSV import batch 化与补偿、demo dataset 生成脚本、备份保留策略、Registry governance 和真实数据隔离。

## 2026-06-14 Beta-5 RC1 Freeze 说明

- Beta-5 RC1 已完成 Release Freeze。当前没有已确认的库存 ledger 破坏性 bug；Critical UAT、Ledger Validation、WS Price Validation 和 Demo Dataset Validation 均通过。
- 新增 release 资产：`docs/releases/beta5-rc1-review.md`、`docs/releases/beta5-rc1.md`、`docs/demo-dataset.md`、`demo-winelist.xlsx`、`demo.db`。
- `demo.db` 是合成演示数据库，版本为 `20260614_0004`，包含 60 bottles、82 ledger transactions、60 个 WS priced bottles；不包含真实个人库存或客户数据。
- 剩余问题的处理顺序建议转入 Beta-6：优先 import compensation、registry governance、CSV import hardening、backup/restore rehearsal 和 sample/demo/real data isolation。

## 2026-06-13 新增说明

- 本地数据库迁移已引入 Alembic baseline。剩余风险从“没有迁移工具”转为“旧库 schema 若偏离当前模型，需要专门增量 migration，不应靠删除数据库解决”。
- CSV confirm 已改为单批次事务提交。剩余导入风险转为“CSV 尚未复用 import batch 历史，且没有人工回滚/撤销流程”，库存 ledger 本身仍保留每瓶 `IN` transaction。
- WineList Stock 真实库存导入已新增 import batch 审计表、atomic confirm 和批次详情 review。剩余风险转为“人工撤销/补偿和更细的人工匹配确认尚未实现”。
- Beta-1A Registry Foundation 已新增 canonical key、alias/mapping/review/finding 表和 Registry Quality 页面。剩余风险转为“review queue 只读、alias approve/reject 和 merge planning 尚未实现”，且任何未来合并都不能自动迁移 Bottle 外键或改写 Ledger。
- Beta-2 Registry Search & Discovery 已新增统一搜索、只读详情和 discovery 页面。剩余风险转为“搜索阈值和 alias provenance 还需要真实样本继续校准”，且 search 命中不能被当作自动合并或审批依据。
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
| P2 | CSV import 尚未复用 import batch 历史和补偿向导。 | WineList batch 已可补偿，但 CSV 仍难以按批次追踪来源文件、导入行数和后续修正。 | 复用 WineList import batch 审计模式；撤销仍应通过 ledger 补偿交易而不是删除原始交易。 |
| P2 | Demo dataset 生成流程尚未固化为脚本。 | `demo-winelist.xlsx` 和 `demo.db` 已生成并校验，但后续重新生成需要按文档步骤或重新执行 seed 流程。 | Beta-6C 可加入受控 demo seed 脚本；脚本仍必须走 ImportService 和 InventoryService。 |
| P2 | Backup & Restore 还没有保留策略或定期提醒。 | 用户可以手动备份和恢复，但长期使用时仍可能忘记备份或保留过多敏感备份文件。 | Beta-6C 可增加备份演练 checklist、保留策略和敏感文件提示；不要默认上传云端。 |
| P2 | Registry Review Queue 当前只读。 | 80-95 分匹配、alias 冲突和疑似重复可见，但不能在 UI 中处理状态。 | 后续增加人工处理状态和备注；不要让处理动作直接改写正式库存。 |
| P2 | Alias Registry 尚无人工 approve/reject UI。 | `approved` alias 才能稳定匹配，但当前缺少用户确认入口。 | 增加 alias 管理页面或在 Registry Quality 中补操作；冲突 alias 必须先复核。 |
| P2 | Registry Search 的 fuzzy/partial 阈值仍是本地启发式。 | 短查询、跨语言简称和相近酒名可能需要更多真实样本校准。 | 保持搜索结果显示 `matched_text/matched_by/score/quality_status`，后续用 WineList 样本和人工反馈调阈值。 |
| P2 | Registry Discovery 的 recent new entity 只按 `created_at` 排序。 | 暂不能区分手工创建、WineList 导入或未来 CSV batch 来源。 | 后续可把 import mapping/import batch provenance 聚合到 discovery item。 |
| P2 | `merged_into_id` 只是治理标记。 | 疑似重复可以被标记，但系统不会迁移旧 Bottle 或改写 Ledger。 | 后续如做合并规划，应先生成可审计 plan，不直接执行外键迁移。 |
| P2 | 酒标草稿没有持久化 draft/reject 历史。 | 用户关闭页面后只能重新上传并生成草稿。 | 增加 label draft 表或 intake session 表，仍保持确认前不落正式库存。 |
| P3 | 已上传酒标图片没有详情页回看。 | 确认后用户不能从 bottle detail 查看已归档图片。 | 增加受控本地静态文件读取或 media asset 关联。 |

## 产品限制

| 优先级 | 限制 | 影响 | 建议处理 |
| --- | --- | --- | --- |
| P1 | CSV 导入要求目标酒柜和位置已存在。 | 初次迁移数据前需要先建酒柜位置。 | 增加模板和预检查清单；是否自动创建位置需另行确认。 |
| P2 | CSV 导入没有 import batch 历史和人工补偿流程。 | 用户难以按批次追踪来源文件、导入行数和后续修正。 | 可复用 WineList import batch 审计模式；补偿应通过 ledger 补偿交易而不是删除原始交易。 |
| P2 | Excel 导入只支持 `WineList.xlsx` 的 `Stock` sheet。 | 其他 sheet、其他 Excel 模板和通用 xlsx 库存表仍不能直接导入。 | 后续先做模板化映射和人工字段匹配，不做自动推断或外部数据补全。 |
| P2 | RC1 demo workbook 是 WineList-compatible synthetic sample，不是通用导入模板。 | 演示数据可用于 demo 和 UAT baseline，但不能代表用户任意 Excel 都可导入。 | 在 demo 和 release notes 中持续标注支持边界。 |
| P2 | 酒标识别当前只是 mock filename heuristic。 | 只能作为流程演示，不能代表真实识别能力。 | 后续按 `docs/14-label-intake-ai-adapter.md` 接入本地 OCR/AI adapter。 |
| P2 | 当前价格、适饮期、产区和类型都来自人工录入或 CSV 字段。 | 不代表权威数据。 | 保留来源、置信度和 manual 标记。 |
| P3 | 没有拖拽式酒柜移动。 | 移动效率有限。 | 等 ledger 和位置规则稳定后再做拖拽。 |

## 风险

| 优先级 | 风险 | 建议处理 |
| --- | --- | --- |
| P1 | 真实库存数据库或真实购买记录被误提交。 | 保持 `.gitignore`，不要提交 `data/`、真实图片和本地数据库；文档持续提醒。 |
| P1 | 未来导入或价格模块绕过 ledger 直接改库存快照。 | 所有库存变更必须经过 InventoryService 和 InventoryTransaction 测试。 |
| P2 | 导入字段含糊导致重复 Producer/Wine/Vintage。 | 增加导入前匹配预览和人工合并流程。 |
| P2 | Alias 被误当作合并依据。 | 保持 alias 与 merge 分离；只有 approved alias 可稳定匹配，conflict/candidate/observed 不应自动命中。 |
| P2 | 搜索结果被误当作权威 registry 判定。 | 搜索只提供发现和核验入口；所有合并、审批、库存变更仍需独立人工确认流程。 |
| P2 | 价格数据来源合规风险。 | 只做 manual/csv/screenshot/link note provider，不实现反爬或批量抓取。 |
| P2 | Demo WS Price 被误解为真实估值或投资指标。 | 在 release notes、demo docs 和 UI 文案中保持 WS Price 为 synthetic/manual reference；正式估值应进入 future provider/snapshot scope。 |
| P2 | 备份文件被误提交或长期散落在仓库目录。 | 备份文件包含完整本地库存、购买价格、送礼对象和估值字段，应视为敏感数据。 |
| P3 | 前端 smoke 基于 jsdom，不能覆盖真实浏览器布局。 | 关键布局稳定后补 Playwright 或浏览器截图 QA。 |
