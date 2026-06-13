# Alpha Demo 限制说明

## 2026-06-13 补充

- 已支持规则化适饮期状态、近期可喝清单、过期风险清单和酒窖健康分。
- 这些洞察只使用本地已有字段和服务器当前日期，不接入专家酒评库、价格 API、AI 判断或外部抓取。
- 健康分是透明的库存运营提示，不是专业品鉴、投资、估值或购买建议。

本文件记录当前本地 Alpha Demo 的能力边界，避免把演示版本误解为完整产品。

## 已支持

- 本地单用户 FastAPI + SQLite 后端。
- React 前端 Dashboard、藏酒列表、酒瓶详情、新增入库、酒柜地图、Transaction 历史。
- 酒柜创建、编辑，以及按行列批量生成位置。
- 手动创建酒庄、酒款、年份、单瓶 bottle，并写入 `IN` transaction。
- MOVE、CONSUME、GIFT、DAMAGE、ADJUST 库存操作，全部保留 ledger。
- 位置容量校验，避免把新 bottle 或 MOVE 目标放入已满位置。
- Bottle detail 显示当前状态、位置、购买信息、适饮期和完整 transaction 时间线。
- Dashboard 显示库存状态、适饮期计数、国家/类型分布、酒柜占用和最近 transaction。
- 藏酒列表支持按酒庄、酒款、年份、状态、位置、国家/类型和备注做本地筛选。
- `/api/export/bottles.csv` 支持导出当前 bottle 库存快照。
- CSV 导入支持“上传/选择文件 -> 解析草稿 -> 逐行错误 -> 用户确认”；解析阶段不写正式库存，确认阶段通过 `IN` transaction 入库。
- 酒标图片 intake 支持“本地图片上传 -> mock 草稿 -> 用户编辑确认”；确认阶段通过 `IN` transaction 入库。

## 尚未支持

- Excel 导入尚未实现；CSV 导入确认当前要求目标酒柜和位置已存在。
- 标签关联尚未接入前端表单；当前只能用备注承载临时描述。
- 真实 OCR/AI 识别尚未接入；当前酒标草稿只使用文件名 mock heuristic，未来 AI 也只能生成草稿，不能直接入库。
- 已上传酒标图片暂未通过静态文件服务在详情页回看；当前前端只在上传当次显示本地预览。
- 价格 provider 尚未实现；当前只有手工购买价和导出字段。
- 没有云同步、账号、权限、多用户、支付、电商、社区或推荐引擎。
- 没有拖拽式酒柜操作；位置移动通过明确 MOVE 表单完成。
- 已有 Alembic baseline migration；但如果旧 SQLite 库 schema 已偏离当前模型，仍需要先备份并编写专门增量 migration，不能靠静默删除数据库解决。

## 演示注意事项

- 请不要把真实酒标图片、真实库存数据库、API key、cookie 或账号信息提交进仓库。
- 当前适饮期、产区、类型、购买价都来自用户手动录入或导入字段，不代表权威结论。
- `Bottle.current_status` 和 `Bottle.current_location_id` 只是查询快照；审计依据始终是 `InventoryTransaction`。
- 删除和批量覆盖类操作暂不开放，避免误删本地私人数据。
