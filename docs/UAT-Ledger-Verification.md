# UAT Ledger Consistency Verification

Last updated: 2026-06-14

## Purpose

Ledger Truth Check verifies that the current Bottle snapshot agrees with the latest `InventoryTransaction` for every bottle.

The project rule is:

```text
InventoryTransaction is the audit truth.
Bottle.current_status and Bottle.current_location_id are query snapshots.
```

## What To Verify

| Check | Expected Result |
| --- | --- |
| Every Bottle has at least one ledger event | No `NO_LEDGER` rows |
| Latest `IN` event | Bottle is `in_stock`, current location equals `to_location_id` |
| Latest `MOVE` event | Bottle is `in_stock`, current location equals `to_location_id` |
| Latest `CONSUME` event | Bottle is `drunk`, current location is null |
| Latest `GIFT` event | Bottle is `gifted`, current location is null |
| Latest `DAMAGE` event | Bottle is `damaged`, current location is null |
| Latest `ADJUST` with `to_location_id` | Bottle is `in_stock`, current location equals `to_location_id` |
| Latest `ADJUST` without `to_location_id` | Bottle is `lost`, current location is null |
| Orphan ledger events | No transaction should reference a missing Bottle |

## SQLite Script

Run against the UAT SQLite database:

```powershell
cd D:\MyLife\17_葡萄酒管理系统
sqlite3 .\apps\api\wine_cellar.db ".read docs/sql/uat-ledger-truth-check.sqlite.sql"
```

Script file:

```text
docs/sql/uat-ledger-truth-check.sqlite.sql
```

## PostgreSQL Script

For a future PostgreSQL deployment, run:

```powershell
psql "$env:WINE_CELLAR_DATABASE_URL" -f docs/sql/uat-ledger-truth-check.postgresql.sql
```

Script file:

```text
docs/sql/uat-ledger-truth-check.postgresql.sql
```

## Pass Criteria

- `ledger_snapshot_mismatches` returns zero rows.
- `ledger_truth_summary.mismatch_count = 0`.
- `orphan_inventory_transactions` returns zero rows.
- Any mismatch must be treated as a UAT blocker because it means a write path bypassed or diverged from ledger truth.

## Investigation Notes

If a mismatch appears:

1. Record the `bottle_id`, latest transaction ID, expected status/location, and actual status/location.
2. Check whether the action was created by WineList import, manual bottle creation, legacy `/inventory-transactions`, or Beta-4 action API.
3. Do not repair by directly editing `bottles.current_status` or `bottles.current_location_id`.
4. Design a ledger compensation or migration-safe repair separately.

