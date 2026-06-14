# UAT WS Price Verification

Last updated: 2026-06-14

## Purpose

Verify that Beta-5 WS Price behaves as manual/imported reference data:

- Imported from `WineList.xlsx` sheet `Stock`, column `WS Price`.
- Stored on `bottles.ws_price`.
- Returned by Bottle and Collection APIs.
- Aggregated by Analytics as `SUM(bottle.ws_price)` and `COUNT(bottle.ws_price IS NOT NULL)`.

This verification does not call Wine-Searcher, scrape prices, or assert that imported reference prices are authoritative.

## Manual Verification Flow

1. Upload `UAT-WineList.xlsx` through WineList draft.
2. Confirm import after row validation passes.
3. Open Import Batch Detail and identify at least one row with non-empty `WS Price`.
4. Open one created bottle from that row.
5. Verify:
   - `GET /api/bottles/{id}` returns `ws_price`.
   - `GET /api/collection/bottles/{id}` returns the same `ws_price`.
   - Analytics Overview shows Total WS Value and WS priced bottle count.
6. Run the SQL script and compare database totals with API totals.

## SQLite Script

```powershell
cd D:\MyLife\17_葡萄酒管理系统
sqlite3 .\apps\api\wine_cellar.db ".read docs/sql/uat-ws-price-verification.sqlite.sql"
```

Script file:

```text
docs/sql/uat-ws-price-verification.sqlite.sql
```

## PostgreSQL Script

```powershell
psql "$env:WINE_CELLAR_DATABASE_URL" -f docs/sql/uat-ws-price-verification.postgresql.sql
```

Script file:

```text
docs/sql/uat-ws-price-verification.postgresql.sql
```

## Pass Criteria

- Import row to Bottle comparison returns zero mismatches.
- `database_total_ws_value` equals Analytics `inventory.total_ws_value`.
- `database_ws_priced_bottles` equals Analytics `inventory.ws_priced_bottles`.
- Blank WS Price rows remain null and are not counted.
- Invalid WS Price values are rejected at draft and never confirmed into Bottle rows.

## Known Limits

- `ws_price` is treated as CNY reference value in Beta-5.
- No currency field, price date, source URL, price history, ROI, or valuation snapshot is created.
- `SUM(ws_price)` is a simple snapshot aggregate, not a market valuation model.

