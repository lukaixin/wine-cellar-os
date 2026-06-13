---
name: alpha-qa-regression
description: Choose and document minimal regression checks for Wine Cellar OS Alpha workflows. Use when Codex makes behavior-preserving changes or touches UI/API flows such as ledger, CSV import/export, label intake, dashboard, or cellar operations.
---

# name

alpha-qa-regression

## description

用于给 Alpha Demo 改动选择并执行最小但足够的回归验证，避免“只是重构”或“只是流程微调”在不经意间破坏酒柜、库存、CSV、酒标或 dashboard 行为。

## when to use

- 进行行为保持型重构。
- 修改前后端接口、库存交互、CSV 导入导出、酒标 intake、Dashboard 展示时。
- 需要决定应跑 `pytest`、`test:ui`、`build`、`qa:alpha` 中哪些命令时。
- 需要产出一份可复查的轻量回归结论时。

## when not to use

- 不用于纯文档、纯 skill、新增说明文字等不影响运行行为的改动。
- 不用于数据库迁移设计本身；迁移任务优先走 `migration-safety-review`。
- 不用于替代更细的单元测试设计。

## required checks

- 先读取 `AGENTS.md`、`README.md`、`docs/progress.md`。
- 根据改动文件选择最小充分验证，不默认跑重测试。
- 若触及库存规则、CSV confirm、酒标确认入库，至少检查对应 API/QA 覆盖是否仍在。
- 若触及前端页面或类型，至少评估 `npm.cmd run test:ui` 和 `npm.cmd run build` 是否需要执行。
- 若触及跨模块主流程，再决定是否需要 `npm.cmd run qa:alpha`。
- 在结论里明确哪些命令已运行、哪些因范围原因被跳过。

## expected final output

- 一份回归验证清单。
- 已运行命令和结果摘要。
- 被跳过的检查及其理由。
