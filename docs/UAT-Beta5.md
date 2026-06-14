# Beta-5 UAT Package

Last updated: 2026-06-14

## Scope

This UAT package validates the Beta-5 Analytics Foundation release without adding product behavior. It covers:

- Import: WineList draft/confirm, duplicate import, invalid import, WS Price import.
- Registry: Producer Search, Wine Search, Alias Search, Discovery, read-only quality surfaces.
- Collection: Search, filter, pagination, Bottle Detail.
- Bottle: Single-bottle identity, location, status, WS Price display.
- Timeline: Import, Consume, Gift, Move, Damage, ordering.
- Inventory Actions: Consume, Gift, Move, Damage, invalid quantity, negative or excessive consume, invalid Location.
- Analytics: Inventory Overview, Consumption Dashboard, Activity Dashboard, WS Value.
- WS Price: import, storage, API exposure, analytics aggregation.

Out of scope:

- New features, schema changes, API changes, UI changes, analytics expansion, price crawling, external price APIs, merge/approval workflows, rollback wizard.

## Test Environment

| Item | Value | Source |
| --- | --- | --- |
| API Version | `wine-cellar-api 0.1.0` | `apps/api/pyproject.toml` |
| Frontend Version | `wine-cellar-web 0.1.0` | `apps/web/package.json` |
| Database Version | Alembic head `20260614_0004` | `apps/api/migrations/versions/20260614_0004_bottle_ws_price.py` |
| Database Engine | SQLite local UAT database | Default local-first assumption |
| Test Data | `UAT-WineList.xlsx`, sheet `Stock` | Generated for this package |

Recommended setup:

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
python -m uvicorn app.main:app --reload

cd D:\MyLife\17_葡萄酒管理系统\apps\web
npm.cmd run dev
```

Recommended post-UAT verification:

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python -m pytest -q

cd D:\MyLife\17_葡萄酒管理系统\apps\web
npm.cmd run build
npm.cmd run test:ui
npm.cmd run qa:alpha
```

## UAT Coverage Matrix

| Module | Required Coverage | Case IDs |
| --- | --- | --- |
| Import | WineList import, duplicate import, invalid import, WS Price import | UAT-IMP-001 to UAT-IMP-005 |
| Registry | Producer Search, Wine Search, Alias Search, Discovery | UAT-REG-001 to UAT-REG-005 |
| Collection | Search, filter, pagination, Bottle Detail | UAT-COL-001 to UAT-COL-005 |
| Bottle | Detail identity, status/location, WS Price | UAT-COL-004, UAT-WS-003 |
| Timeline | Import, Consume, Gift, Move, Damage, sorting | UAT-TL-001 to UAT-TL-006 |
| Inventory Actions | Consume, Gift, Move, Damage, validation, negative/excess/invalid location | UAT-ACT-001 to UAT-ACT-008 |
| Analytics | Inventory Overview, Consumption, Activity, WS Value | UAT-AN-001 to UAT-AN-004 |
| WS Price | Import, storage, API, analytics calculation | UAT-WS-001 to UAT-WS-005 |

## UAT Cases

Status values: `Not Run`, `Passed`, `Failed`, `Blocked`.

| Case ID | Module | Precondition | Steps | Expected Result | Actual Result | Status |
| --- | --- | --- | --- | --- | --- | --- |
| UAT-IMP-001 | Import | Fresh UAT database migrated to `20260614_0004`; API and frontend running; `UAT-WineList.xlsx` available. | Open Inventory Import; upload `UAT-WineList.xlsx`; run WineList draft. | Draft succeeds; sheet is `Stock`; all 10 rows are valid; no Producer/Wine/Vintage/Bottle/InventoryTransaction is created during draft; location summary shows all target locations. |  | Not Run |
| UAT-IMP-002 | Import | UAT-IMP-001 draft exists and all rows are valid. | Confirm the draft import; open Import Batch History and Batch Detail. | Confirm returns created Bottle IDs and `IN` transaction IDs; batch status becomes confirmed; created bottle count equals the sum of `Quantity`; every imported bottle is `in_stock`. |  | Not Run |
| UAT-IMP-003 | Import | UAT-IMP-002 completed. | Upload the same `UAT-WineList.xlsx` again and run draft. | Duplicate rows are marked invalid with already-confirmed row errors; no second set of bottles can be confirmed from the same source rows. |  | Not Run |
| UAT-IMP-004 | Import | Copy `UAT-WineList.xlsx` to a local throwaway file. | Change one row to invalid values such as `Quantity=-1`, `Vintage=abc`, or `WS Price=-50`; upload and draft. | Draft reports row-level errors; confirm is blocked; no formal inventory or ledger rows are created from invalid rows. |  | Not Run |
| UAT-IMP-005 | Import | `UAT-WineList.xlsx` includes populated `WS Price` values. | Run draft and inspect row normalized data; confirm import; inspect imported Bottle Detail. | Draft displays normalized `ws_price`; confirm persists `bottles.ws_price` on every expanded bottle from rows with WS Price. |  | Not Run |
| UAT-REG-001 | Registry | UAT import confirmed. | Search a known producer from UAT data, for example `Domaine Test Rayas`. | Producer result appears with expected display name, score, quality status, and detail panel. |  | Not Run |
| UAT-REG-002 | Registry | UAT import confirmed. | Search a known wine name from UAT data, for example `Grand Rouge`. | Wine result appears under Wine results and links to producer context; no inventory or ledger mutation occurs. |  | Not Run |
| UAT-REG-003 | Registry | Registry alias fixture exists from import or manual test setup. | Search an alias value from UAT data, for example `UAT DRC Alias` or `UAT Rayas Alias`. | Matching result shows `matched_by=alias` or equivalent alias indication; alias search does not merge records. |  | Not Run |
| UAT-REG-004 | Registry | UAT import confirmed. | Open Registry Discovery. | Recent producers, wines, and vintages include UAT-created entities; quality risks are visible if generated; page is read-only. |  | Not Run |
| UAT-REG-005 | Registry | UAT import confirmed. | Open Registry Quality and inspect Findings, Review Queue, Alias, Import Mapping. | Import mappings exist for WineList rows; review queue/finding rows are observable when generated; no approve/reject or merge action is required for Beta-5. |  | Not Run |
| UAT-COL-001 | Collection | UAT import confirmed. | Open Collection Explorer; search by producer, wine, vintage, and mixed tokens. | Matching bottle groups appear; results are Bottle inventory groups, not standalone registry entities. |  | Not Run |
| UAT-COL-002 | Collection | UAT import confirmed with multiple locations and vintages. | Apply Producer, Vintage, Location, and Status filters one at a time. | Result count and visible groups update according to each filter; filtering does not change inventory. |  | Not Run |
| UAT-COL-003 | Collection | UAT import confirmed with more than one page or configured small page size. | Move between pages using pagination controls. | Offset/page changes return the next result slice; total count stays stable; no duplicate or missing group is observed across pages. |  | Not Run |
| UAT-COL-004 | Collection | UAT import confirmed. | Expand a collection group; click a specific bottle; inspect Detail tab. | Detail shows bottle ID, status, producer, wine, vintage, bottle size, location, acquisition/import context, and WS Price when present. |  | Not Run |
| UAT-COL-005 | Collection | UAT import confirmed. | Search by alias or Chinese/English mixed text when aliases/names exist. | Matching inventory groups are discoverable through registry-aware local search; no governance action is triggered. |  | Not Run |
| UAT-TL-001 | Timeline | UAT import confirmed; select an imported bottle. | Open Bottle Detail Timeline. | Timeline contains an `IN` or Import event from `InventoryTransaction`; quantity delta is `+1`. |  | Not Run |
| UAT-TL-002 | Timeline | Select an in-stock bottle. | Perform Consume action; reopen Timeline. | Timeline shows `CONSUME` as latest event; quantity delta is `-1`; bottle status is `drunk`. |  | Not Run |
| UAT-TL-003 | Timeline | Select an in-stock bottle. | Perform Gift action with recipient and note; reopen Timeline. | Timeline shows `GIFT`; notes combine recipient/reason and user note; bottle status is `gifted`. |  | Not Run |
| UAT-TL-004 | Timeline | Select an in-stock bottle and a different valid Location. | Perform Move action; reopen Timeline. | Timeline shows `MOVE`; from/to locations are correct; bottle remains `in_stock` at target location. |  | Not Run |
| UAT-TL-005 | Timeline | Select an in-stock bottle. | Perform Damage action with reason and note; reopen Timeline. | Timeline shows `DAMAGE`; quantity delta is `-1`; bottle status is `damaged`. |  | Not Run |
| UAT-TL-006 | Timeline | A bottle has Import plus at least two later events in sequence. | Inspect Timeline ordering. | Events are sorted newest first in Collection Timeline; legacy bottle transaction list remains chronological where applicable. |  | Not Run |
| UAT-ACT-001 | Inventory Actions | Select an in-stock bottle. | Submit Consume with quantity `1`. | API/UI succeeds; ledger writes `CONSUME`; bottle snapshot becomes `drunk` with no current location. |  | Not Run |
| UAT-ACT-002 | Inventory Actions | Select an in-stock bottle. | Submit Gift with quantity `1`, recipient, and notes. | API/UI succeeds; ledger writes `GIFT`; bottle snapshot becomes `gifted`; recipient is visible through timeline notes. |  | Not Run |
| UAT-ACT-003 | Inventory Actions | Select an in-stock bottle and another valid location with capacity. | Submit Move with current from location and target location. | API/UI succeeds; ledger writes `MOVE`; bottle snapshot location changes to target; status remains `in_stock`. |  | Not Run |
| UAT-ACT-004 | Inventory Actions | Select an in-stock bottle. | Submit Damage with reason and notes. | API/UI succeeds; ledger writes `DAMAGE`; bottle snapshot becomes `damaged`; no current location remains. |  | Not Run |
| UAT-ACT-005 | Inventory Actions | Select any in-stock bottle. | Submit Consume/Gift/Damage with `quantity=0` or `quantity=-1` through API or dev tools. | Request is rejected by validation; no ledger event is created; bottle snapshot is unchanged. |  | Not Run |
| UAT-ACT-006 | Inventory Actions | Select any in-stock bottle. | Submit Consume/Gift/Damage with `quantity=2`. | Request is rejected as over-consumption for a single Bottle instance; no ledger event is created. |  | Not Run |
| UAT-ACT-007 | Inventory Actions | Select a bottle already consumed, gifted, or damaged. | Try Consume, Gift, Damage, or Move again. | Request is rejected as already unavailable or not in stock; no duplicate outbound ledger event is created. |  | Not Run |
| UAT-ACT-008 | Inventory Actions | Select an in-stock bottle. | Submit Move with stale `from_location` or missing `to_location`. | Request returns conflict/not found validation; no ledger event is created; snapshot remains unchanged. |  | Not Run |
| UAT-AN-001 | Analytics | UAT import confirmed. | Open Analytics Overview. | Total bottles, wines, producers, vintages, status distribution, country/region/vintage distributions match imported data and current bottle snapshots. |  | Not Run |
| UAT-AN-002 | Analytics | At least one Consume, Gift, and Damage action has been performed. | Open Analytics Consumption. | Last 30 days, Last 90 days, All Time, and monthly trend reflect `CONSUME`, `GIFT`, and `DAMAGE` ledger events only. |  | Not Run |
| UAT-AN-003 | Analytics | Import and several actions have been performed. | Open Analytics Activity. | Recent Activity lists `IMPORT`, `CONSUME`, `GIFT`, `MOVE`, and `DAMAGE` events from ledger in newest-first order. |  | Not Run |
| UAT-AN-004 | Analytics | Imported bottles include WS Price. | Open Analytics Overview and WS Price section. | Total WS Value equals `SUM(bottles.ws_price)` for non-null values; WS priced bottle count equals `COUNT(ws_price)`. |  | Not Run |
| UAT-WS-001 | WS Price | `UAT-WineList.xlsx` has non-empty `WS Price` rows. | Upload file and inspect draft rows. | Each row with WS Price shows normalized two-decimal value; blank WS Price remains null; negative/non-number values are row errors. |  | Not Run |
| UAT-WS-002 | WS Price | UAT-WS-001 draft is valid. | Confirm import and query/import batch detail. | Each imported row stores created bottle IDs; every created bottle from a priced row receives that row's `ws_price`. |  | Not Run |
| UAT-WS-003 | WS Price | UAT import confirmed. | Call `GET /api/bottles/{id}` and `GET /api/collection/bottles/{id}` for a priced bottle. | Both APIs return the same `ws_price` as the imported row. |  | Not Run |
| UAT-WS-004 | WS Price | UAT import confirmed. | Call `GET /api/analytics/summary`. | `inventory.total_ws_value` equals database `SUM(ws_price)` and `inventory.ws_priced_bottles` equals database `COUNT(ws_price)`. |  | Not Run |
| UAT-WS-005 | WS Price | UAT import confirmed. | Run `docs/sql/uat-ws-price-verification.sqlite.sql` against the UAT SQLite database. | SQL output shows no import storage mismatches and matching analytics totals. |  | Not Run |

## Acceptance Notes

- Any failed case should capture browser/API evidence, database path, API/frontend versions, database version, and reproduction steps in `docs/UAT-Report-Template.md`.
- UAT operators should not edit real user inventory databases. Use a dedicated UAT database or restore from backup before testing.
- WS Price is manual/imported reference data. It is not a live Wine-Searcher integration, market value guarantee, ROI metric, or price history.

