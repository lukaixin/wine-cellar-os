# Beta-5 Critical UAT Report

Release: Beta-5 Analytics Foundation  
Database Version: `20260614_0004`  
Tester: Codex Critical UAT execution  
Test Date: 2026-06-14  
Environment / Database Path: `D:\MyLife\17_葡萄酒管理系统\tmp\beta5-critical-uat\beta5-critical-uat.db`  
API: `http://127.0.0.1:18100`  
Frontend: `http://127.0.0.1:5174`  

## Summary

Critical UAT executed against an isolated SQLite UAT database, not the production/default local database. `UAT-WineList.xlsx` was imported through the real API, four real inventory actions were executed through action APIs, and Bottle, Timeline, Analytics, WS Price, API docs, and frontend rendering were verified.

Result: PASS. No failed or blocked scoped UAT cases.

## Passed

| Case ID | Module | Evidence |
| --- | --- | --- |
| UAT-IMP-002 | Import | WineList draft/confirm through API created 11 bottles and 11 `IN` ledger transactions; batch `00247fe7-1800-45e6-88c8-219b8cbd7330` confirmed. |
| UAT-COL-001 | Collection | `GET /collection/search?q=UAT` returned 10 pre-action search groups through API; frontend Collection Explorer rendered 11 post-action groups after status/location split. |
| UAT-COL-004 | Collection | Collection bottle detail returned selected bottle `eb374472-0258-4059-8fc6-7690096f7774`, status `in_stock`, WS Price `880.00`; frontend detail drawer rendered. |
| UAT-TL-001 | Timeline | Imported bottle timeline contained `IN` with `quantity_delta=1`; frontend Timeline tab rendered `+1 bottle` and WineList import note. |
| UAT-ACT-001 | Inventory Actions | Consume API wrote transaction `ba46bdf7-52dd-4d42-a916-fe99d0541594`; bottle `8625c1a0-67d6-4917-ae37-c31675aa263e` became `drunk`; timeline head `CONSUME`. |
| UAT-ACT-002 | Inventory Actions | Gift API wrote transaction `edb85751-177f-48f6-aa8d-37b32b5d81e2`; bottle `0fd673f6-3579-4c2d-aa57-cb581b0d4435` became `gifted`; timeline head `GIFT`. |
| UAT-ACT-003 | Inventory Actions | Move API wrote transaction `9f27cbe5-862f-4ac8-9589-8b3a8019c517`; bottle `1f108c56-f548-4411-90da-b3e45a8b38cc` remained `in_stock` at `Critical UAT Move Cellar / UAT-MOVE-01`; timeline head `MOVE`. |
| UAT-ACT-004 | Inventory Actions | Damage API wrote transaction `7cdbb938-9360-4c93-8eed-8bde4de74dea`; bottle `4be77eb5-2972-4040-8e44-94bba62c1425` became `damaged`; timeline head `DAMAGE`. |
| UAT-AN-001 | Analytics | Analytics inventory returned 11 bottles, 10 wines, 10 producers, 10 vintages; status distribution `in_stock=8`, `drunk=1`, `gifted=1`, `damaged=1`. |
| UAT-AN-002 | Analytics | Analytics all-time consumption returned consumed `1`, gifted `1`, damaged `1` from ledger events. |
| UAT-AN-003 | Analytics | Analytics recent activity included `IMPORT`, `CONSUME`, `GIFT`, `MOVE`, and `DAMAGE`. |
| UAT-AN-004 | Analytics | Analytics `total_ws_value=21600.00`, `ws_priced_bottles=11`, matching database SQL totals. |
| UAT-WS-003 | WS Price | `GET /api/bottles/{id}` and `GET /api/collection/bottles/{id}` both returned WS Price `880.00` for bottle `eb374472-0258-4059-8fc6-7690096f7774`. |
| UAT-WS-004 | WS Price | API Analytics total WS value `21600.00` matched database `SUM(ws_price)=21600.0`; priced bottle count matched `11`. |

## Failed

| Case ID | Module | Expected | Actual | Evidence | Issue ID |
| --- | --- | --- | --- | --- | --- |
| None |  |  |  |  |  |

## Blocked

| Case ID | Module | Blocker | Owner | Next Step |
| --- | --- | --- | --- | --- |
| None |  |  |  |  |

## SQL Validation

| Check | Result |
| --- | --- |
| Ledger Truth Check | `ledger_truth_summary`: `bottle_count=11`, `mismatch_count=0`; mismatch query returned 0 rows; orphan transaction query returned 0 rows. |
| WS Price Import-to-Bottle Check | mismatch query returned 0 rows. |
| WS Price Total | `database_total_ws_value=21600.0`, `database_ws_priced_bottles=11`, `database_total_bottles=11`. |
| WS Price by Status | `damaged=3000.0`, `drunk=4800.0`, `gifted=2600.0`, `in_stock=11200.0`; total `21600.0`. |

Note: `sqlite3.exe` was not available in PATH, so the same SQL files were executed through Python `sqlite3` against the isolated UAT database.

## Release Readiness

| Area | Result | Evidence |
| --- | --- | --- |
| API docs | Passed | `/docs` rendered; `/openapi.json` exposed `/api/analytics/summary`, `/analytics/summary`, `/collection/search`, `/api/collection/search`, `/collection/bottles/{bottle_id}`, `/collection/bottles/{bottle_id}/timeline`, `/inventory/actions/consume`, `/inventory/actions/gift`, `/inventory/actions/move`, `/inventory/actions/damage`. |
| Frontend Analytics | Passed | Browser rendered Analytics with 11 bottles, WS total `¥21,600.00`, Status Distribution, Consumption, WS Price Coverage, and Recent Activity. |
| Frontend Collection / Bottle / Timeline / Actions | Passed | Browser rendered Collection Explorer, expandable groups, detail drawer, Timeline tab, and Actions tab. |
| Database | Passed | Alembic version query returned `20260614_0004`. |

Screenshots:

- `output/playwright/beta5-critical-uat-api-docs.png`
- `output/playwright/beta5-critical-uat-analytics.png`
- `output/playwright/beta5-critical-uat-collection.png`

Raw evidence:

- `tmp/beta5-critical-uat/critical-uat-evidence.json`
- `tmp/beta5-critical-uat/sql-validation-results.json`
- `tmp/beta5-critical-uat/frontend-docs-evidence.json`

## Issues

| Issue ID | Severity | Area | Description | Reproduction | Proposed Handling |
| --- | --- | --- | --- | --- | --- |
| None |  |  |  |  |  |

## Risk

| Risk | Impact | Mitigation / Decision |
| --- | --- | --- |
| UAT database is temporary | Evidence DB under `tmp/` can be deleted by cleanup. | Preserve JSON evidence and screenshots for review; rerun UAT from `UAT-WineList.xlsx` if needed. |
| SQLite CLI unavailable | Cannot use `.read` command exactly from docs on this machine. | Python `sqlite3` executed the same SQL file contents and produced passing results. |
| Scope is Critical UAT subset only | Non-critical UAT cases remain unexecuted in this run. | Accept for Critical UAT release gate; run full UAT separately if broader manual sign-off is required. |

## Sign Off

| Role | Name | Decision | Date | Notes |
| --- | --- | --- | --- | --- |
| Product Owner | Pending user sign-off | Pending | 2026-06-14 | Critical UAT result is PASS from execution evidence. |
| Engineering | Codex | PASS | 2026-06-14 | Ledger, WS Price, API docs, frontend render, and scoped API flows passed. |
| UAT Tester | Codex | PASS | 2026-06-14 | No failed or blocked scoped cases. |

## Release Recommendation

PASS
