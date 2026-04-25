-- Q4: Top 10 wallets by total transaction volume with profile enrichment
-- Business question: Who are our highest-value customers and what is their profile?
-- Complexity: Multi-source JOIN (fact + unified dim), aggregation, LIMIT

SELECT
    t.wallet_id,
    u.kyc_tier,
    u.account_status,
    u.acquisition_channel,
    u.state,
    u.age,
    COUNT(*)                                    AS tx_count,
    SUM(t.amount_ngn)                           AS total_volume_ngn,
    SUM(t.fee_ngn)                              AS total_fees_ngn,
    MAX(CASE WHEN t.fraud_flag THEN 1 ELSE 0 END) AS has_fraud_history,
    MAX(CASE WHEN t.churn_30d  THEN 1 ELSE 0 END) AS is_churned
FROM fact_mobile_money_tx t
JOIN dim_unified_wallet u ON t.wallet_id = u.wallet_id
GROUP BY
    t.wallet_id, u.kyc_tier, u.account_status,
    u.acquisition_channel, u.state, u.age
ORDER BY total_volume_ngn DESC
LIMIT 10;
