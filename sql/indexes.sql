-- RetainIQ Pipeline — Indexing Strategy
-- Partial indexes on fraud_flag/churn_30d filter to only TRUE rows,
-- reducing index size and speeding up rare-event queries.

-- fact_mobile_money_tx
CREATE INDEX IF NOT EXISTS idx_mmtx_wallet   ON fact_mobile_money_tx (wallet_id);
CREATE INDEX IF NOT EXISTS idx_mmtx_ts       ON fact_mobile_money_tx (timestamp);
CREATE INDEX IF NOT EXISTS idx_mmtx_type     ON fact_mobile_money_tx (transaction_type);
CREATE INDEX IF NOT EXISTS idx_mmtx_kyc      ON fact_mobile_money_tx (kyc_tier);
CREATE INDEX IF NOT EXISTS idx_mmtx_channel  ON fact_mobile_money_tx (channel);
CREATE INDEX IF NOT EXISTS idx_mmtx_fraud    ON fact_mobile_money_tx (fraud_flag)  WHERE fraud_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_mmtx_churn    ON fact_mobile_money_tx (churn_30d)   WHERE churn_30d  = TRUE;

-- fact_xml_transactions
CREATE INDEX IF NOT EXISTS idx_xml_wallet    ON fact_xml_transactions (wallet_id);
CREATE INDEX IF NOT EXISTS idx_xml_type      ON fact_xml_transactions (transaction_type);
CREATE INDEX IF NOT EXISTS idx_xml_paying    ON fact_xml_transactions (paying_at);
CREATE INDEX IF NOT EXISTS idx_xml_ref_dup   ON fact_xml_transactions (is_ref_dup)  WHERE is_ref_dup = TRUE;
CREATE INDEX IF NOT EXISTS idx_xml_anomaly   ON fact_xml_transactions (date_order_anomaly) WHERE date_order_anomaly = TRUE;

-- dim_unified_wallet  (the main JOIN target for analytical queries)
CREATE INDEX IF NOT EXISTS idx_unified_status ON dim_unified_wallet (account_status);
CREATE INDEX IF NOT EXISTS idx_unified_kyc    ON dim_unified_wallet (kyc_tier);
CREATE INDEX IF NOT EXISTS idx_unified_churn  ON dim_unified_wallet (churn_30d)  WHERE churn_30d = TRUE;
CREATE INDEX IF NOT EXISTS idx_unified_lang   ON dim_unified_wallet (preferred_language);
