---
name: wine-registry-normalization
description: Normalize Producer/Wine/Vintage registry data for Wine Cellar OS. Use when Codex needs to design or review import mappings, alias cleanup, deduping rules, or manual normalization workflows without collapsing bottle-level inventory concepts.
---

# name

wine-registry-normalization

## description

用于梳理 `Producer`、`Wine`、`Vintage` 三层注册表的标准化任务，尤其适合导入映射、别名合并、命名清洗和人工复核清单整理。

## when to use

- 设计或调整样例导入字段到 `Producer` / `Wine` / `Vintage` 的映射规则。
- 处理重复酒庄名、混合中英法命名、别名归并和年份拆层问题。
- 评估是否需要先做 registry 清洗，再进入 bottle 或 inventory 流程。
- 编写或评审标准化说明、人工确认步骤、低置信映射清单。

## when not to use

- 不用于 `Bottle` 库存状态、位置移动、出入库事务校验。
- 不用于数据库 schema 迁移设计。
- 不用于价格抓取、OCR、外部百科补全或任何外部 API 调用。
- 不用于只改前端样式或纯展示文案的任务。

## required checks

- 先读取 `AGENTS.md`、`docs/04-data-model.md`、`docs/09-compliance-data-policy.md`。
- 明确保持 `Wine`、`Vintage`、`Bottle` 分层，不把三者压成一张表或一个对象。
- 对无法确定的国家、产区、别名、年份保留 `unknown` / `manual` / `low confidence` 语义，不伪造权威值。
- 记录每条标准化规则的来源：样例表头、现有字段、人工判断，避免“看起来合理”的隐式合并。
- 若任务会影响导入流程，明确哪些字段只是 registry 层清洗，哪些字段仍需用户确认后才能生成正式库存。

## expected final output

- 一份可执行的标准化规则或映射草案。
- 一份需要人工确认的歧义项清单。
- 若有改动，给出受影响文件、验证命令和未覆盖的边界。
