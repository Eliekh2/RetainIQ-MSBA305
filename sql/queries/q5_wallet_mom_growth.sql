-- Q5: Month-over-month volume growth per wallet — top 5 fastest-growing
-- Business question: Which wallets show the steepest growth trajectory?
-- Complexity: CTE + window function (LAG) + computed percentage growth

WITH monthly AS (
    SELECT
        wallet_id,
        DATE_TRUNC('month', timestamp)  AS month,
        SUM(amount_ngn)                 AS monthly_volume,
        COUNT(*)                        AS monthly_tx_count
    FROM fact_mobile_money_tx
    GROUP BY wallet_id, DATE_TRUNC('month', timestamp)
),
growth AS (
    SELECT
        wallet_id,
        month,
        monthly_volume,
        monthly_tx_count,
        LAG(monthly_volume) OVER (PARTITION BY wallet_id ORDER BY month) AS prev_month_volume,
        ROUND(
            100.0 * (
                monthly_volume
                - LAG(monthly_volume) OVER (PARTITION BY wallet_id ORDER BY month)
            )
            / NULLIF(
                LAG(monthly_volume) OVER (PARTITION BY wallet_id ORDER BY month),
                0
            ),
            2
        ) AS pct_growth
    FROM monthly
)
SELECT
    wallet_id,
    month,
    monthly_volume,
    prev_month_volume,
    pct_growth
FROM growth
WHERE pct_growth IS NOT NULL
ORDER BY pct_growth DESC
LIMIT 5;
