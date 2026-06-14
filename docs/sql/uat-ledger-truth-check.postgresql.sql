-- Beta-5 UAT Ledger Truth Check for PostgreSQL.
-- Returns only mismatches and summary counts. Zero mismatches is the pass condition.

WITH latest_transaction AS (
    SELECT
        it.*,
        ROW_NUMBER() OVER (
            PARTITION BY it.bottle_id
            ORDER BY it.occurred_at DESC, it.created_at DESC, it.id DESC
        ) AS rn
    FROM inventory_transactions it
),
ledger_truth AS (
    SELECT
        b.id AS bottle_id,
        b.current_status AS actual_status,
        b.current_location_id AS actual_location_id,
        lt.id AS latest_transaction_id,
        lt.transaction_type AS latest_transaction_type,
        lt.from_location_id,
        lt.to_location_id,
        lt.occurred_at,
        CASE
            WHEN lt.id IS NULL THEN 'NO_LEDGER'
            WHEN lt.transaction_type IN ('IN', 'MOVE') THEN 'in_stock'
            WHEN lt.transaction_type = 'CONSUME' THEN 'drunk'
            WHEN lt.transaction_type = 'GIFT' THEN 'gifted'
            WHEN lt.transaction_type = 'DAMAGE' THEN 'damaged'
            WHEN lt.transaction_type = 'ADJUST' AND lt.to_location_id IS NOT NULL THEN 'in_stock'
            WHEN lt.transaction_type = 'ADJUST' THEN 'lost'
            ELSE 'UNKNOWN_TRANSACTION'
        END AS expected_status,
        CASE
            WHEN lt.transaction_type IN ('IN', 'MOVE') THEN lt.to_location_id
            WHEN lt.transaction_type = 'ADJUST' AND lt.to_location_id IS NOT NULL THEN lt.to_location_id
            ELSE NULL
        END AS expected_location_id
    FROM bottles b
    LEFT JOIN latest_transaction lt
        ON lt.bottle_id = b.id
       AND lt.rn = 1
)
SELECT
    'ledger_snapshot_mismatches' AS check_name,
    bottle_id,
    latest_transaction_id,
    latest_transaction_type,
    expected_status,
    actual_status,
    expected_location_id,
    actual_location_id,
    occurred_at
FROM ledger_truth
WHERE expected_status IN ('NO_LEDGER', 'UNKNOWN_TRANSACTION')
   OR expected_status <> actual_status
   OR COALESCE(expected_location_id, '') <> COALESCE(actual_location_id, '')
ORDER BY bottle_id;

WITH latest_transaction AS (
    SELECT
        it.*,
        ROW_NUMBER() OVER (
            PARTITION BY it.bottle_id
            ORDER BY it.occurred_at DESC, it.created_at DESC, it.id DESC
        ) AS rn
    FROM inventory_transactions it
),
ledger_truth AS (
    SELECT
        b.id AS bottle_id,
        b.current_status AS actual_status,
        b.current_location_id AS actual_location_id,
        lt.id AS latest_transaction_id,
        CASE
            WHEN lt.id IS NULL THEN 'NO_LEDGER'
            WHEN lt.transaction_type IN ('IN', 'MOVE') THEN 'in_stock'
            WHEN lt.transaction_type = 'CONSUME' THEN 'drunk'
            WHEN lt.transaction_type = 'GIFT' THEN 'gifted'
            WHEN lt.transaction_type = 'DAMAGE' THEN 'damaged'
            WHEN lt.transaction_type = 'ADJUST' AND lt.to_location_id IS NOT NULL THEN 'in_stock'
            WHEN lt.transaction_type = 'ADJUST' THEN 'lost'
            ELSE 'UNKNOWN_TRANSACTION'
        END AS expected_status,
        CASE
            WHEN lt.transaction_type IN ('IN', 'MOVE') THEN lt.to_location_id
            WHEN lt.transaction_type = 'ADJUST' AND lt.to_location_id IS NOT NULL THEN lt.to_location_id
            ELSE NULL
        END AS expected_location_id
    FROM bottles b
    LEFT JOIN latest_transaction lt
        ON lt.bottle_id = b.id
       AND lt.rn = 1
)
SELECT
    'ledger_truth_summary' AS check_name,
    COUNT(*) AS bottle_count,
    SUM(
        CASE
            WHEN expected_status IN ('NO_LEDGER', 'UNKNOWN_TRANSACTION')
              OR expected_status <> actual_status
              OR COALESCE(expected_location_id, '') <> COALESCE(actual_location_id, '')
            THEN 1 ELSE 0
        END
    ) AS mismatch_count
FROM ledger_truth;

SELECT
    'orphan_inventory_transactions' AS check_name,
    it.id AS transaction_id,
    it.bottle_id,
    it.transaction_type,
    it.occurred_at
FROM inventory_transactions it
LEFT JOIN bottles b ON b.id = it.bottle_id
WHERE b.id IS NULL
ORDER BY it.occurred_at, it.id;

