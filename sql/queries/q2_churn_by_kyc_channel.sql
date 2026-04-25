-- Q2: Churn rate by KYC tier and channel
-- Business question: Which customer segments and channels have the highest churn?
-- Complexity: Conditional aggregation + NULLIF + multiple GROUP BY dimensions

SELECT
    kyc_tier,
    channel,
    COUNT(DISTINCT wallet_id)                                       AS wallet_count,
    SUM(CASE WHEN churn_30d THEN 1 ELSE 0 END)                     AS churned_wallets,
    ROUND(
        SUM(CASE WHEN churn_30d THEN 1 ELSE 0 END)::NUMERIC
        / NULLIF(COUNT(DISTINCT wallet_id), 0) * 100, 2
    )                                                               AS churn_rate_pct,
    ROUND(AVG(amount_ngn), 2)                                       AS avg_tx_amount
FROM fact_mobile_money_tx
GROUP BY kyc_tier, channel
ORDER BY churn_rate_pct DESC;
