-- Q1: Monthly transaction volume, count, and fees
-- Business question: How has the mobile money platform grown month-over-month?
-- Complexity: Aggregation + DATE_TRUNC (foundational)

SELECT
    DATE_TRUNC('month', timestamp)  AS month,
    COUNT(*)                        AS tx_count,
    SUM(amount_ngn)                 AS total_volume_ngn,
    SUM(fee_ngn)                    AS total_fees_ngn,
    AVG(amount_ngn)                 AS avg_tx_amount
FROM fact_mobile_money_tx
GROUP BY 1
ORDER BY 1;
