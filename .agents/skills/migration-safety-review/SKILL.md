---
name: migration-safety-review
description: Review SQLite and Alembic migration safety for Wine Cellar OS. Use when Codex changes models, migrations, backup steps, or schema evolution plans and needs to check data retention, incremental upgrades, and no-drop safety constraints.
---

# name

migration-safety-review

## description

用于在模型或迁移改动前后做 SQLite + Alembic 安全评审，重点检查备份、增量迁移、数据保留和是否意外破坏 Alpha 现有库存数据。

## when to use

- 修改 `apps/api/app/models`、`apps/api/migrations`、`docs/16-database-migrations.md` 时。
- 准备新增字段、表、索引或约束前。
- 评审某个变更是否真的需要 migration，还是只是代码层调整。
- 检查迁移方案是否会破坏现有 SQLite 本地库。

## when not to use

- 不用于纯前端、纯文档、纯 skill 维护任务。
- 不用于只读数据分析或样例文件画像。
- 不用于绕过迁移直接删库重建的“快捷方案”。

## required checks

- 先读取 `AGENTS.md`、`docs/16-database-migrations.md`、`docs/04-data-model.md`、`docs/progress.md`。
- 明确是否需要新增 migration；如果需要，说明原因和升级路径。
- 验证方案不依赖 `drop_table`、静默删库、批量清空或隐式数据重写。
- 检查新字段是否优先 nullable 或带安全 default，避免破坏已有行。
- 检查备份命令、验证命令、旧库偏离 schema 的残余风险。
- 确认迁移不会伪造或篡改 `InventoryTransaction` 历史。

## expected final output

- 一份 go / no-go 安全评审结论。
- 一份迁移步骤、备份步骤和验证命令。
- 一份需要用户额外确认的风险或兼容性说明。
