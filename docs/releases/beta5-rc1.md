# Beta-5 RC1 Release Notes

## Release Date

2026-06-14

## Version

Beta-5 RC1

## Features

### Import

- CSV draft import and confirm workflow.
- WineList `Stock` sheet draft/confirm workflow.
- Import batch list/detail review.
- Atomic confirm with rollback on write failure.
- WineList `WS Price` column import into `Bottle.ws_price`.

### Registry

- Producer/Wine/Vintage canonical key foundation.
- Registry alias, import mapping, review queue, and quality finding tables.
- Registry Quality read-only page.
- Registry Search and Discovery read-only APIs and UI.

### Collection

- Collection search by local inventory.
- Producer, Vintage, Location, and Status filters.
- Pagination.
- Grouped bottle results.
- Bottle detail drawer.

### Timeline

- Bottle timeline sourced from `InventoryTransaction`.
- Import, Move, Consume, Gift, and Damage events.
- Newest-first timeline in Collection bottle detail.

### Inventory Actions

- Consume action.
- Gift action.
- Move action.
- Damage action.
- Validation for single-bottle quantity, stale location, invalid location, and duplicate outbound attempts.

### Analytics

- Read-only Analytics Summary API and UI.
- Inventory overview and distributions.
- Consumption periods.
- Monthly consumption trend.
- Recent activity from ledger events.

### WS Price

- Nullable `Bottle.ws_price`.
- WineList `WS Price` validation during draft.
- Bottle API and Collection Bottle Detail API expose `ws_price`.
- Analytics computes `total_ws_value = SUM(bottles.ws_price)` and `ws_priced_bottles`.

## Database Version

Alembic head: `20260614_0004`

Migration chain:

- `20260613_0001_initial_alpha_schema.py`
- `20260613_0002_import_batches.py`
- `20260613_0003_registry_foundation.py`
- `20260614_0004_bottle_ws_price.py`

## Test Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Automated Tests | PASS | `python -m pytest -q`, `67 passed in 30.64s`. |
| Frontend Build | PASS | `npm.cmd run build`. |
| UI Tests | PASS | `npm.cmd run test:ui`. |
| Alpha QA | PASS | `npm.cmd run qa:alpha`. |
| Critical UAT | PASS | Passed 14, Failed 0, Blocked 0. |
| Ledger Validation | PASS | `mismatch_count = 0`, orphan transaction rows `0`. |
| WS Price Validation | PASS | Database WS total matched API/Analytics total. |
| Demo Dataset Validation | PASS | `demo.db` has 60 bottles, 82 ledger rows, 0 orphan transactions, 0 snapshot mismatches. |

## Upgrade Notes

Before upgrading a local SQLite database:

```powershell
cd D:\MyLife\17_葡萄酒管理系统\apps\api
python scripts\backup_sqlite_db.py
python -m alembic upgrade head
```

Notes:

- `20260614_0004` only adds nullable `bottles.ws_price`.
- No Bottle foreign keys are rewritten.
- No ledger transaction history is deleted or rewritten.
- Existing WineList import rows remain audit records.

## Known Limitations

- WineList import only supports the fixed `Stock` sheet format.
- WS Price is imported/manual reference data, not live Wine-Searcher integration or market valuation.
- No price history, ROI, currency model, portfolio return, or provider adapter is implemented.
- Registry governance is read-only or observation-first; approve/reject and merge planning are not implemented.
- Import compensation and rollback wizard are not implemented.
- Label intake uses a mock filename heuristic and is not real OCR/AI.
- No cloud sync, account system, multi-user permissions, ecommerce, recommendation, or community feature exists.
- Root-level `pytest` is not the canonical test command; run API tests from `apps/api`.

## Next Milestone

Beta-6 should focus on release hardening rather than new product expansion:

1. Import compensation design and implementation.
2. Registry governance workflow.
3. Registry Search provenance and filters.
4. CSV import hardening.
5. Local backup/restore drill.
6. Label intake persistence/image playback if retained in scope.

