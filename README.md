# 葡萄酒管理系统 / Wine Cellar OS

本仓库用于构建一个**本地优先的私人酒窖管理系统**。第一阶段目标不是做“葡萄酒社区”或“中国版 Vivino”，而是解决个人/家庭/小型私宴场景里的酒窖管理闭环：

- 酒标识别与人工确认
- 酒款、年份、容量、单瓶实例的标准化管理
- 酒柜位置管理
- 入库、出库、移动、饮用、送礼、损耗、盘点调整的可追溯记录
- 适饮期提醒
- 市场价格快照与资产视图
- 未来采购、消耗建议
- 本地大屏与备份导出

## 当前阶段

`v0.4-local-alpha-demo`

当前已建立本地 FastAPI 后端、SQLite + SQLAlchemy 数据模型、基础 CRUD API、库存 transaction workflow，以及 Vite + React + TypeScript 前端 Alpha Demo。前端已支持酒柜/位置管理、批量生成位置、手动入库、酒标图片本地上传与草稿确认入库、库存操作、藏酒搜索筛选、酒柜占用视图、Dashboard 适饮期洞察、CSV 导出和安全 CSV 导入草稿。AI/OCR 识别、价格 provider、云同步、账号系统尚未实现。

## MVP 产品边界

第一版只做本地 MVP：

1. 酒柜二维建模
2. 酒瓶手动录入
3. 酒标照片归档
4. 酒款标准化字段
5. 库存 ledger
6. 搜索筛选
7. 适饮期提醒
8. 大屏概要
9. CSV/Excel 导入导出
10. 本地备份恢复

暂不做：

- 社区
- 电商
- 自动大规模价格爬虫
- 复杂 3D 酒窖
- 多租户 SaaS
- 自动估值承诺
- 自动采购下单

## 推荐技术方向

本地优先，后续可迁移云端：

- Backend: FastAPI + SQLAlchemy/SQLModel + SQLite
- Frontend: Next.js 或 React SPA
- Search: SQLite FTS5
- Image storage: 本地文件目录 + 数据库存 hash/path
- Export: CSV / Excel / PDF
- AI intake: 图片识别生成草稿，必须人工确认后入库

## 本地开发命令

前置要求：

- Python 3.11+，并确保 `python` 可在当前 PowerShell 中执行。
- Node.js 20+，并确保 `npm.cmd` 可在当前 PowerShell 中执行。
- 如果 `python` 提示“无法识别”，请先安装 Python 并勾选 Add Python to PATH，或用本机 Python 解释器完整路径替代下面命令中的 `python`。

后端位于 `apps/api`，使用 FastAPI + SQLAlchemy + SQLite。

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
python -m uvicorn app.main:app --reload
```

默认 SQLite 数据库为 `apps/api/wine_cellar.db`。如需指定路径，可设置：

```powershell
$env:WINE_CELLAR_DATABASE_URL = "sqlite:///./data/dev.db"
```

前端位于 `apps/web`，使用 Vite + React + TypeScript。

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\web
npm.cmd install
npm.cmd run build
npm.cmd run dev
```

前端 smoke test 使用 Vitest + jsdom，不需要连接手工浏览器：

```powershell
npm.cmd run test:ui
```

Alpha QA 自动化套件会先执行前端生产构建和 UI smoke test，再启动临时 FastAPI 服务验证酒柜、入库、MOVE、出库、ADJUST、transaction timeline、Dashboard、CSV 导出、CSV 导入草稿/确认，以及酒标图片上传、草稿生成和确认入库：

```powershell
npm.cmd run qa:alpha
```

如果当前 PowerShell 中 `python` 不在 PATH，可先指定解释器路径：

```powershell
$env:WINE_CELLAR_PYTHON = "C:\Path\To\python.exe"
npm.cmd run qa:alpha
```

`qa:alpha` 默认使用 `127.0.0.1:18000`、`apps/api/.alpha-qa-smoke.db` 临时数据库和 `apps/api/.alpha-qa-data` 临时上传目录，执行结束后会清理临时文件。

前端默认调用 `http://127.0.0.1:8000`。如需修改 API 地址，复制或参考 `apps/web/.env.example`：

```powershell
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
```

常用本地地址：

```text
Backend: http://127.0.0.1:8000
Health:  http://127.0.0.1:8000/health
API docs: http://127.0.0.1:8000/docs
Frontend: http://127.0.0.1:5173
```

## Alpha Demo 工作流

1. 启动后端和前端。
2. 在“酒柜地图”中创建酒柜，使用“批量生成位置”创建二维位置。
3. 在“新增入库”中创建或选择酒庄、酒款、年份和位置，填写购入信息与可选适饮期。
4. 在“酒标入库”中上传 jpg/png/webp 酒标图片，生成低置信草稿，人工编辑字段和位置后确认入库。
5. 在“藏酒列表”中按酒庄、酒款、年份、状态、位置、国家/类型或备注搜索。
6. 在“酒瓶详情”中执行 MOVE、CONSUME、GIFT、DAMAGE、ADJUST，并查看完整 transaction 时间线。
7. 在 Dashboard 查看库存状态、适饮期提醒、国家/类型分布、酒柜占用和最近 transaction。
8. 使用页面右上角“导出 CSV”，或直接访问：

```text
http://127.0.0.1:8000/api/export/bottles.csv
```

CSV 当前支持导出和安全导入草稿。导入不会在解析阶段创建酒瓶或 transaction；只有用户确认全部有效行后，后端才会通过 `IN` ledger 规则创建库存。

导入 CSV 最小字段：

```csv
producer_name,wine_name,vintage_year,bottle_size_ml,cellar_name,location_code
```

可选字段：

```text
country,region,type,purchase_price,purchase_currency,purchase_date,purchase_source,drink_from,drink_to,notes,tags
```

导入确认前必须先存在目标 `cellar_name + location_code`。确认时会重新校验目标位置和容量；如果存在无效行或容量超限，不会直接修改库存。`tags` 当前只在草稿中解析展示，确认导入暂不写入标签关系。

## 给 Codex 的入口

让 Codex 从仓库根目录读取：

1. `AGENTS.md`
2. `docs/00-project-brief.md`
3. `docs/02-mvp-scope.md`
4. `docs/04-data-model.md`
5. `docs/10-codex-task-backlog.md`

库存状态与 transaction 规则见 `docs/12-inventory-rules.md`。Alpha Demo 限制见 `docs/13-alpha-demo-limitations.md`。酒标 intake 与未来 AI/OCR adapter 边界见 `docs/14-label-intake-ai-adapter.md`。

当前本地 Alpha Demo 已建立。下一条可执行任务建议使用：

```text
Read AGENTS.md and current docs. Refactor apps/web/src/App.tsx into focused page/components without changing behavior. Keep existing backend rules, label intake, CSV import/export, and alpha QA passing. Do not add AI integration, scraping, cloud sync, auth, payment, community, or recommendation engine.
```
