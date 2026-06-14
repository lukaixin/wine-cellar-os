-- Beta-5 UAT WS Price verification for SQLite.
-- Compare import row WS Price, stored Bottle WS Price, and analytics-ready SUM/COUNT.

.headers on
.mode column

WITH imported_bottles AS (
    SELECT
        ib.source_filename,
        ibr.source_row_number,
        json_extract(ibr.normalized_row, '$.ws_price') AS imported_ws_price,
        value AS bottle_id
    FROM import_batches ib
    JOIN import_batch_rows ibr ON ibr.batch_id = ib.id
    JOIN json_each(ibr.created_bottle_ids)
    WHERE ib.status = 'confirmed'
      AND ibr.status = 'imported'
)
SELECT
    'import_to_bottle_ws_price_mismatches' AS check_name,
    imported_bottles.source_filename,
    imported_bottles.source_row_number,
    imported_bottles.bottle_id,
    imported_bottles.imported_ws_price,
    b.ws_price AS stored_ws_price
FROM imported_bottles
JOIN bottles b ON b.id = imported_bottles.bottle_id
WHERE (
        imported_bottles.imported_ws_price IS NULL
        AND b.ws_price IS NOT NULL
    )
   OR (
        imported_bottles.imported_ws_price IS NOT NULL
        AND b.ws_price IS NULL
    )
   OR (
        imported_bottles.imported_ws_price IS NOT NULL
        AND b.ws_price IS NOT NULL
        AND ROUND(CAST(imported_bottles.imported_ws_price AS NUMERIC), 2) <> ROUND(CAST(b.ws_price AS NUMERIC), 2)
    )
ORDER BY imported_bottles.source_filename, imported_bottles.source_row_number, imported_bottles.bottle_id;

SELECT
    'database_ws_price_totals' AS check_name,
    ROUND(COALESCE(SUM(ws_price), 0), 2) AS database_total_ws_value,
    COUNT(ws_price) AS database_ws_priced_bottles,
    COUNT(*) AS database_total_bottles
FROM bottles;

SELECT
    'ws_price_by_status' AS check_name,
    current_status,
    ROUND(COALESCE(SUM(ws_price), 0), 2) AS status_ws_value,
    COUNT(ws_price) AS status_ws_priced_bottles,
    COUNT(*) AS status_total_bottles
FROM bottles
GROUP BY current_status
ORDER BY current_status;
