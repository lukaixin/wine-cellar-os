# 本地数据库迁移策略

最后更新：2026-06-14

Wine Cellar OS Alpha 默认使用本地 SQLite。随着字段和表继续增加，不能再把“删除并重建数据库”作为常规升级方式；正式库存数据升级前必须先备份，再运行迁移。

## 选择方案

当前采用 Alembic + SQLAlchemy：

- 现有后端已经使用 SQLAlchemy declarative models，Alembic 能复用同一套 metadata。
- Alembic 支持 SQLite 文件数据库，不要求 Postgres、云服务或外部运行时。
- Alembic 会记录 `alembic_version`，后续可以做增量 schema 变更。
- 初始 baseline migration 对已有 Alpha 表做存在性检查，避免在已有 SQLite 库上因为表已存在而失败。

## 文件位置

- `apps/api/alembic.ini`
- `apps/api/migrations/env.py`
- `apps/api/migrations/versions/20260613_0001_initial_alpha_schema.py`
- `apps/api/migrations/versions/20260613_0002_import_batches.py`
- `apps/api/migrations/versions/20260613_0003_registry_foundation.py`
- `apps/api/migrations/versions/20260614_0004_bottle_ws_price.py`
- `apps/api/migrations/versions/20260614_0005_beta6_safety_foundation.py`
- `apps/api/scripts/backup_sqlite_db.py`

## 初始化或升级数据库

在 `apps/api` 目录运行：

```powershell
python -m pip install -e ".[dev]"
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
```

默认数据库路径是 `apps/api/wine_cellar.db`。如需使用其他 SQLite 文件：

```powershell
$env:WINE_CELLAR_DATABASE_URL = "sqlite:///D:/path/to/wine_cellar.db"
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
```

## 备份规则

`backup_sqlite_db.py` 只复制文件，不修改数据库。

- 如果数据库存在，会复制到同目录 `backups/` 下，文件名带时间戳。
- 如果数据库不存在，会提示 `nothing to back up`，不会创建或删除数据库。
- 如果不是文件型 SQLite URL，脚本会拒绝处理。

## 重置本地开发库

只在明确不需要保留开发数据时执行：

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python scripts\backup_sqlite_db.py
Remove-Item -LiteralPath .\wine_cellar.db
python -m alembic upgrade head
```

不要对真实库存库执行静默删除。删除前应确认备份文件存在且可读。

## 迁移编写约束

- 新增模型字段或表后，在 `apps/api` 目录运行 `python -m alembic revision --autogenerate -m "describe change"`，检查生成内容后再提交。
- 不写会删除用户数据的 migration。
- 不使用 `drop_table`、批量覆盖或清空表作为常规升级手段。
- SQLite 上复杂 schema 变更需要单独评估，必要时使用 Alembic batch operations。
- 新字段优先 nullable 或带安全 default，避免破坏已有行。
- 库存状态仍必须以 `InventoryTransaction` 作为审计依据，migration 不应伪造库存事件。
- 导入审计表可以记录来源和创建结果，但 migration 不应代替导入服务创建正式库存。

## 当前限制

- 初始 baseline migration 主要用于创建空库，或给已有当前 Alpha schema 写入 Alembic 版本记录。
- 如果用户手里的旧数据库 schema 已经偏离当前模型，baseline 不会自动补齐所有列级差异；需要先备份，再写专门的增量 migration。
- FastAPI 启动仍保留当前本地开发的 `create_all` 行为；正式升级流程应使用 `python -m alembic upgrade head`。
- `import_batches/import_batch_rows` 只记录导入批次审计，不提供自动撤销；撤销应另行设计 ledger 补偿流程。
- `20260613_0003_registry_foundation` 只新增 registry 治理字段和只读观察表，回填 Producer/Wine key，不迁移 Bottle 外键、不修改 ledger、不做自动合并。
- `20260614_0004_bottle_ws_price` 只给 `bottles` 新增 nullable `ws_price` 字段，不修改 ledger、不回填价格、不创建估值历史。
- `20260614_0005_beta6_safety_foundation` 只给 `import_batches` 新增 nullable compensation 字段，并新增 `safety_events` 表；不删除 import rows、不改写原始 `IN` ledger、不自动生成补偿交易。
