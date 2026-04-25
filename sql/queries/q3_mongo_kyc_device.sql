-- Q3: Distribution of customer profiles by KYC tier and account status
-- Business question: What is the demographic composition of our customer base?
-- Source: MongoDB customer_profiles (MQL aggregation pipeline below)
-- Note: Executed via pymongo in notebook 06; SQL version runs on dim_unified_wallet

-- SQL version (runs against dim_unified_wallet after integration):
SELECT
    kyc_tier,
    account_status,
    preferred_language,
    COUNT(*)                         AS profile_count,
    ROUND(AVG(age), 1)               AS avg_age,
    COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ()  AS pct_of_total
FROM dim_unified_wallet
GROUP BY kyc_tier, account_status, preferred_language
ORDER BY profile_count DESC
LIMIT 20;

-- MQL equivalent (run via pymongo in notebook 06):
-- pipeline = [
--     {"$group": {
--         "_id": {"kyc_tier": "$kyc_tier", "account_status": "$account_status"},
--         "count": {"$sum": 1},
--         "avg_age": {"$avg": "$age"}
--     }},
--     {"$sort": {"count": -1}}
-- ]
-- list(mongo_db.customer_profiles.aggregate(pipeline))
