# Beta-6 Backup & Restore

最后更新：2026-06-14

## 目标

Backup & Restore 用于降低本地 SQLite 酒窖数据风险。它提供受控的手动备份、可校验恢复和安全事件记录，服务于本地单用户使用场景。

本能力不引入云同步、多用户权限、远程备份或数据库托管。

## 支持范围

- 文件型 SQLite 数据库。
- 手动创建本地备份文件。
- 从本地备份文件恢复。
- 恢复前自动创建 pre-restore backup。
- 记录 `BACKUP_CREATED` 与 `RESTORE_COMPLETED` safety event。
- 恢复后继续使用现有 Inventory、Timeline、Analytics 查询路径。

## 数据模型

新增 `safety_events` 表：

- `id`
- `event_type`
- `artifact_name`
- `artifact_path`
- `artifact_sha256`
- `reason`
- `actor`
- `event_metadata`
- `created_at`

当前 event type：

- `BACKUP_CREATED`
- `RESTORE_COMPLETED`

## API

### List Backups

`GET /admin/backups`

等价路径：

`GET /api/admin/backups`

响应包含：

- 当前数据库路径。
- backup directory。
- 备份文件列表。
- 每个备份的 filename、path、size、sha256、created_at。

### Create Backup

`POST /admin/backups`

等价路径：

`POST /api/admin/backups`

行为：

- 复制当前 SQLite 文件到同目录 `backups/`。
- 文件名包含微秒级时间戳。
- 不覆盖旧备份。
- 计算 SHA-256。
- 写入 `BACKUP_CREATED` safety event。

### Restore Backup

`POST /admin/backups/restore`

等价路径：

`POST /api/admin/backups/restore`

请求体：

```json
{
  "filename": "wine_cellar-20260614-120000-000000.db.bak",
  "confirmation_text": "RESTORE",
  "reason": "UAT restore rehearsal"
}
```

恢复前校验：

- `filename` 不能包含路径。
- 文件必须存在于 backup directory。
- SQLite `PRAGMA quick_check` 必须返回 `ok`。
- `alembic_version.version_num` 必须等于当前版本 `20260614_0005`。
- `confirmation_text` 必须严格等于 `RESTORE`。

恢复行为：

- 如果当前数据库文件存在，先创建 `pre-restore` 备份。
- 释放当前应用 engine 连接。
- 用指定备份覆盖当前数据库文件。
- 再次释放 engine 连接，确保后续请求使用恢复后的数据库。
- 在恢复后的数据库中写入 `RESTORE_COMPLETED` safety event。

## UI

新增 `Safety Admin` 页面：

- 显示当前 database path 与 backup directory。
- 列出已有 backup 文件、大小、SHA-256 和创建时间。
- 提供 `Create Backup` 按钮。
- Restore 表单要求填写原因、输入 `RESTORE`、勾选确认，并触发浏览器确认框。

## 迁移

迁移文件：

`apps/api/migrations/versions/20260614_0005_beta6_safety_foundation.py`

迁移策略：

- 新增 `safety_events` 表。
- 不修改库存 ledger。
- 不修改 Analytics、Registry 或 Bottle domain。
- 不删除任何用户数据。

## 验证

推荐命令：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python -m pytest tests\test_safety_service.py tests\test_migrations.py -q
```

覆盖重点：

- 备份文件名唯一且不覆盖。
- 备份记录 `BACKUP_CREATED` safety event。
- 恢复需要 typed confirmation。
- 恢复前生成 pre-restore backup。
- 恢复后 Collection、Timeline、Analytics 查询仍正常。
- 恢复记录 `RESTORE_COMPLETED` safety event。

## 操作边界

- 只支持文件型 SQLite；`sqlite:///:memory:`、PostgreSQL、远程数据库不在当前范围。
- 恢复只接受当前 Alembic version 的备份文件。
- 当前没有定时备份、加密备份、云端同步或备份保留策略。
- 备份文件仍是敏感本地数据，不应提交到仓库。
