# Demo Dataset Package

Date: 2026-06-14  
Release: Beta-5 RC1  
Artifacts:

- `demo-winelist.xlsx`
- `demo.db`
- `output/release/demo-winelist-preview.png`

## Purpose

This package provides a synthetic demo dataset for Beta-5 RC1 demonstrations and manual verification. It is not personal inventory, customer data, scraped data, or a market-price dataset.

## Dataset Summary

| Item | Value |
| --- | --- |
| Workbook | `demo-winelist.xlsx` |
| Workbook sheet | `Stock` |
| Workbook rows | 60 |
| Database | `demo.db` |
| Database version | `20260614_0004` |
| Bottles | 60 |
| Producers | 46 |
| Locations | 4 |
| Registry aliases | 16 synthetic aliases |
| WS priced bottles | 60 |
| SQL WS Price total | `55650.00` |
| Analytics WS Price total | `55650.00` |

## Coverage

Geography:

- France: Bordeaux, Burgundy, Rhone, Champagne.
- Italy: Tuscany, Piedmont.
- Spain: Rioja, Ribera del Duero.
- USA: Napa Valley, Sonoma, Oregon.
- Australia: Barossa, Margaret River.

Inventory status:

| Status | Bottle count |
| --- | ---: |
| `in_stock` | 44 |
| `drunk` | 8 |
| `gifted` | 5 |
| `damaged` | 3 |

Ledger events:

| Transaction type | Row count |
| --- | ---: |
| `IN` | 60 |
| `MOVE` | 6 |
| `CONSUME` | 8 |
| `GIFT` | 5 |
| `DAMAGE` | 3 |

Locations:

- `法国朋友家 / FR`
- `家中酒柜 / C`
- `家中散放 / HOME-OUTSIDE`
- `Demo Display Cellar / SHELF-A`

## Creation Method

`demo-winelist.xlsx` was generated as a WineList-compatible workbook with a `Stock` sheet. `demo.db` was created by:

1. Running Alembic migrations to `20260614_0004`.
2. Importing `demo-winelist.xlsx` through the existing WineList draft/confirm service.
3. Creating `IN` ledger rows through existing import confirm behavior.
4. Applying Move, Consume, Gift, and Damage through `InventoryService.apply_transaction`.
5. Adding synthetic Registry Alias rows for search demonstration.

No application feature, database schema, inventory action logic, ledger logic, analytics logic, or registry governance logic was changed to create this dataset.

## Validation Results

The demo database was checked after generation:

```text
alembic_version = 20260614_0004
bottle_count = 60
status_counts = damaged 3, drunk 8, gifted 5, in_stock 44
transaction_counts = IN 60, MOVE 6, CONSUME 8, GIFT 5, DAMAGE 3
ws_total_sql = 55650.00
ws_total_analytics = 55650.00
orphan_transactions = 0
snapshot_mismatch = 0
```

## Demo Path

Recommended demo sequence:

1. Start API with `WINE_CELLAR_DATABASE_URL` pointed at `demo.db`.
2. Start the frontend.
3. Open Analytics first to show total bottles, status distribution, WS Price total, consumption, and recent activity.
4. Open Collection Explorer and filter by Country/Region/Location/Status.
5. Open a moved in-stock bottle and show Detail plus Timeline with `IN` and `MOVE`.
6. Open a consumed/gifted/damaged bottle and show Timeline plus final status.
7. Open Registry Search and search a demo producer or alias.
8. Open Inventory Import and show `demo-winelist.xlsx` as the matching source workbook.

## Screenshot Suggestions

- Analytics Overview with WS Price total and Status Distribution.
- Analytics Activity showing Import, Move, Consume, Gift, and Damage.
- Collection Explorer filtered to `in_stock`.
- Bottle Detail with Timeline tab open.
- Registry Search result for a synthetic alias.
- Import Batch Detail for `demo-winelist.xlsx`.

## Running Against Demo DB

PowerShell:

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
$env:WINE_CELLAR_DATABASE_URL = "sqlite:///D:/MyLife/17_葡萄酒管理系统/demo.db"
python -m uvicorn app.main:app --reload
```

In another terminal:

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\web
npm.cmd run dev
```

## Data Boundaries

- The dataset is synthetic and demo-only.
- It does not contain real personal inventory, customer data, purchase history, label images, account data, or private notes.
- WS Price values are synthetic manual reference numbers.
- Do not use this dataset for valuation, investment, purchasing, or market analysis.

