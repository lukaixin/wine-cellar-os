# Beta-5 RC1 Release Readiness Review

Date: 2026-06-14  
Version: Beta-5 RC1  
Recommendation: PASS for local single-user Release Candidate scope

## Overview

Wine Cellar OS Beta-5 RC1 is a local-first, single-user cellar management release. The delivered system covers import, registry discovery, collection browsing, bottle detail and timeline, ledger-backed inventory actions, read-only analytics, and WineList WS Price import.

The system remains intentionally local-first:

- SQLite is the default runtime database.
- Inventory state is maintained through `Bottle` snapshots plus `InventoryTransaction` ledger history.
- WS Price is imported/manual reference data, not a live market price feed.
- AI/OCR, cloud sync, multi-user permissions, recommendation, ecommerce, and price crawling are not part of RC1.

## Completed Domains

| Domain | RC1 status | Evidence |
| --- | --- | --- |
| Import | Completed | CSV draft/confirm, WineList Stock draft/confirm, import batch review, atomic confirm, duplicate detection. |
| Registry | Completed as Beta governance foundation | Canonical keys, alias/import mapping/review/finding tables, Registry Quality, Registry Search and Discovery. |
| Collection | Completed | Collection search, filters, pagination, grouped bottle results, bottle detail drawer. |
| Timeline | Completed | Bottle timeline reads directly from `InventoryTransaction` and supports Import, Move, Consume, Gift, Damage events. |
| Inventory Actions | Completed | Consume, Gift, Move, Damage APIs and UI actions reuse `InventoryService`; no direct snapshot-only write path. |
| Analytics | Completed | Read-only summary API/UI for inventory, distributions, consumption periods, monthly trend, recent activity. |
| WS Price | Completed | `Bottle.ws_price`, WineList `WS Price` draft/confirm, Bottle/Collection API exposure, Analytics `SUM(ws_price)`. |

## Stable Features

Stable for RC1 means the capability is in scope for local Beta-5 use and has automated test coverage plus Critical UAT or ledger/WS verification evidence.

| Feature | Status | Notes |
| --- | --- | --- |
| Core domain model: Producer, Wine, Vintage, Bottle, Cellar, Location, InventoryTransaction | Stable | Model separation is preserved. |
| Alembic SQLite migrations through `20260614_0004` | Stable | Current database version is `20260614_0004`. |
| Ledger-backed inventory state | Stable | Inventory writes go through `InventoryService` and create ledger rows. |
| WineList Stock import for supported template | Stable | Supports fixed `Stock` sheet and `WS Price`; not a generic Excel mapper. |
| Import Batch Review | Stable for read-only audit | History/detail surfaces exist; compensation workflow remains future work. |
| Collection Explorer | Stable | Search/filter/pagination/detail passed Beta-5 UAT. |
| Bottle Detail and Timeline | Stable | Timeline is ledger-backed and newest-first in Collection detail. |
| Consume/Gift/Move/Damage actions | Stable | Validation covers quantity, stale location, invalid location, duplicate outbound attempts. |
| Analytics Foundation | Stable for read-only summary | No cached analytics table or predictive model. |
| WS Price Analytics | Stable for imported/manual reference totals | SQL and API totals matched in UAT and demo validation. |

Validated gates:

- Automated tests: `python -m pytest -q` passed, `67 passed in 30.64s`.
- Frontend build: `npm.cmd run build` passed.
- UI tests: `npm.cmd run test:ui` passed.
- Alpha smoke: `npm.cmd run qa:alpha` passed.
- Critical UAT: Passed 14, Failed 0, Blocked 0.
- Ledger validation: `mismatch_count = 0`, orphan transaction rows `0`.
- WS Price validation: database total matched API/Analytics total.
- Demo dataset validation: `demo.db` has 60 bottles, 82 ledger transactions, 0 orphan transactions, 0 snapshot mismatches.

## Experimental Features

| Feature | Status | Reason |
| --- | --- | --- |
| Label intake mock draft | Experimental | Uses filename heuristic only; no real OCR/AI; no persistent draft/reject history. |
| Registry governance workflow | Beta / incomplete | Observation tables and search are present, but approve/reject/merge planning is not implemented. |
| Drink window health dashboard | Beta | Rule-based local summary; not a professional drinking recommendation. |
| WS Price as value signal | Beta reference data | Stored and summed, but no currency model, valuation snapshot history, ROI, provider adapter, or live market feed. |

## Known Risks

| Risk | Impact | Current mitigation |
| --- | --- | --- |
| Existing local databases may drift from current schema | Upgrade can fail if an old local DB differs from expected Alpha/Beta schema. | Always backup before Alembic upgrade; add targeted migrations for drift. |
| Import compensation is not implemented | User can audit batch output but cannot safely undo a batch in one guided flow. | Future compensation must use ledger transactions, not transaction deletion. |
| Registry Review Queue is read-only | Users can see suspicious matches but cannot process them in UI. | Keep governance separate from Bottle/Ledger mutations until Beta-6. |
| Alias approval UI is missing | Approved aliases can exist, but there is no full manual review workflow. | Treat aliases as governance metadata; do not auto-merge records. |
| WS Price can be misread as valuation | Users may overinterpret `SUM(ws_price)` as live market value. | Docs and UI copy should keep it as imported/manual reference data. |
| Frontend layout QA is still light | jsdom smoke tests do not fully prove responsive layout quality. | Critical UAT included browser screenshot checks; expand Playwright later. |
| Real data privacy risk | Local DBs, photos, and purchase data are sensitive. | Keep demo data synthetic; do not commit real DBs, images, or customer records. |

## Outstanding Gaps

- No WineList import compensation wizard.
- No generic Excel import mapper beyond supported WineList `Stock` sheet.
- CSV import lacks template download, import batch history reuse, tag persistence, and row filters.
- Registry Review Queue lacks process state changes, notes, approve/reject, and merge planning.
- `merged_into_id` is a governance marker only; no Bottle foreign key migration workflow exists.
- Label intake has no real OCR/AI adapter, no persistent draft/reject history, and no bottle detail image playback.
- Price history, valuation snapshots, ROI, currency handling, market movement, and provider adapters are not implemented.
- No cloud sync, accounts, permissions, multi-user workflow, ecommerce, community, or recommendation engine.
- No formal restore-drill document for `demo.db` or real user SQLite backups.

## Release Structure Review

Current structure is acceptable for RC1. No large-scale file moves are recommended during freeze.

| Area | Current state | Recommendation |
| --- | --- | --- |
| Release | `docs/releases/beta5-rc1-review.md` and `docs/releases/beta5-rc1.md` now hold RC1 release assets. | Keep future versioned release notes under `docs/releases/`. |
| Demo | `demo-winelist.xlsx`, `demo.db`, and `docs/demo-dataset.md` provide the official RC1 demo package. | Beta-6 can add a controlled seed script, but should keep generated DB/workbook clearly synthetic. |
| UAT | `docs/UAT-Beta5.md`, verification docs, SQL files, and UAT report already exist. | Consider moving UAT docs into `docs/uat/` after RC1 only if the file count grows. |
| SQL | UAT SQL scripts are under `docs/sql/`. | Keep validation SQL grouped here. |
| Architecture | Architecture and ADR docs are split across numbered docs and `docs/decisions/`. | No restructure required before Beta-6. |

## RC1 Assessment

Beta-5 qualifies as RC1 for the stated local single-user Beta scope.

The release is not V1 and should not be presented as a production cloud system, real AI/OCR system, live valuation system, or marketplace/recommendation product. RC1 is suitable for:

- Local demo.
- Manual UAT.
- Beta-5 regression baseline.
- Beta-6 planning input.

## Recommended Beta-6 Scope

1. Ledger-safe import compensation workflow for WineList and future CSV batches.
2. Registry Review Queue processing: status, notes, alias approve/reject, and merge planning without automatic Bottle/Ledger mutation.
3. Registry Search hardening: match highlighting, quality filters, alias provenance, fuzzy threshold calibration.
4. CSV import hardening: template download, valid/invalid filters, tag persistence, and import history alignment.
5. Local data safety: backup/restore rehearsal, sample/demo/real data isolation checks.
6. Label intake persistence and bottle detail image playback if label intake remains in near-term scope.
