---
name: valuation-snapshot-design
description: Design valuation snapshot structures and provider boundaries for Wine Cellar OS. Use when Codex is planning manual/csv/screenshot/link-note valuation workflows, field mappings, compliance constraints, or asset-view prerequisites without implementing scraping.
---

# name

valuation-snapshot-design

## description

用于设计估值快照相关的数据流、字段约束和 provider adapter 边界，确保价格只作为 `ValuationSnapshot` 进入系统，而不是直接污染正式库存或伪装成权威行情。

## when to use

- 设计 manual / csv / screenshot / link note 价格录入流程时。
- 评审 `ValuationSnapshot` 字段、导入模板、API contract 或前端录入草稿时。
- 讨论价格来源、置信度、税费/运费口径和多币种展示时。
- 规划资产视图或估值历史前的底层数据结构时。

## when not to use

- 不用于实现受限网站 scraping、反爬绕过或外部价格 API 集成。
- 不用于库存 ledger 逻辑本身。
- 不用于把价格结论写成投资建议、采购建议或绝对判断。

## required checks

- 先读取 `AGENTS.md`、`docs/04-data-model.md`、`docs/09-compliance-data-policy.md`、`docs/roadmap.md`。
- 确认价格来源处于仓库允许范围：`manual` / `csv` / `screenshot` / `link note`。
- 保留 `source`、`source_url`、`captured_at`、`currency`、`confidence` 等审计字段，不伪装为权威实时价格。
- 保持估值快照挂在 `Vintage` 维度，不直接改 `Bottle` 库存状态或 ledger。
- 明确税费、运费、低/均/中位价格口径，以及哪些字段允许 unknown/manual。

## expected final output

- 一份估值快照设计说明或字段映射草案。
- 一份来源/置信度/合规边界说明。
- 若涉及实现，给出验证命令和仍待确认的业务口径。
