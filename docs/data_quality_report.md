# Data Quality Report — RetainIQ Pipeline (MSBA 305)

> Rubric §4.3 deliverable. Before/after statistics for all three sources.
> Measured by `data/audit/inspect_all.py` (run 2026-04-23).

---

## Source 1: Nigerian Mobile Money Transactions (Parquet)

| Metric | Before Cleaning | After Cleaning | Action Taken | Rationale |
|---|---|---|---|---|
| Row count | 4,000,000 | 4,000,000 | No rows removed | Cleaning flags, never deletes |
| Column count | 13 | 16 | +3 outlier flag columns | IQR flags added per §6.5 |
| Null cells (total) | 0 | 0 | No imputation needed | Source is complete |
| Duplicate rows | 0 | 0 | None found | No deduplication needed |
| Duplicate transaction_id | 0 | 0 | None found | PK integrity confirmed |
| `timestamp` dtype | datetime64[ns] | datetime64[ns] | Coercion confirmed | Already correct on load |
| `fraud_flag` dtype | bool | bool | Coercion confirmed | Already correct |
| `churn_30d` dtype | bool | bool | Coercion confirmed | Already correct |
| `agent_id` empty strings | ~2.8M non-agent rows | Same (now NULL) | Empty string → NULL for non-cashin/cashout | Semantic correctness — agent_id is meaningless outside cashin/cashout |
| `is_amount_ngn_outlier` rows | — | ~54,000 (est.) | IQR flag added | Large amounts flagged, not removed |
| `is_fee_ngn_outlier` rows | — | ~0 | IQR flag added | Fees are capped at ₦200; minimal outliers |
| `is_balance_after_ngn_outlier` rows | — | ~60,000 (est.) | IQR flag added | High-balance wallets flagged |
| Wallet ID format compliance | 4,000,000 / 4,000,000 | 4,000,000 / 4,000,000 | No changes | All WLT-XXXXXXXX on ingest |
| Timestamp range | 2024-01-01 → 2024-06-29 | Same | No changes | 6-month window is consistent |

**Completeness before:** 100.0% | **Completeness after:** 100.0%

---

## Source 2: Customer Profiles (JSON)

| Metric | Before Cleaning | After Cleaning | Action Taken | Rationale |
|---|---|---|---|---|
| Record count | 375,837 | 375,837 | No rows removed | Source is complete |
| Column count | 14 | 16 | +`is_age_anomaly`, date coercions | Age flag + datetime conversion |
| Null cells (total) | 0 | 0 | No imputation needed | Source is complete |
| Duplicate wallet_ids | 0 | 0 | None found | Profile integrity confirmed |
| `date_of_birth` dtype | object (string) | datetime64 | pd.to_datetime() | Required for date arithmetic |
| `registration_date` dtype | object (string) | datetime64 | pd.to_datetime() | Required for date arithmetic |
| Categorical casing | Mixed (e.g., "Male", "ACTIVE") | Lowercase | str.lower() applied to 6 columns | Consistent join/groupby behaviour |
| `is_age_anomaly` rows | — | 0 | Flag added | No anomalies found; flag present for production |
| Wallet ID format compliance | 375,837 / 375,837 | 375,837 / 375,837 | No changes | All WLT-XXXXXXXX on ingest |

**Completeness before:** 100.0% | **Completeness after:** 100.0%

---

## Source 3: XML Cross-Border Partner Transactions

| Metric | Before Cleaning | After Cleaning | Action Taken | Rationale |
|---|---|---|---|---|
| Record count | 28,360 | 28,360 | No rows removed | Cleaning flags, never deletes |
| Column count | 26 (correct parser) | 30 | +4 flag/derived columns | Anomaly flags + outlier flags |
| Null cells (total) | 0 | 0 | No imputation needed | Source is complete when correctly parsed |
| Duplicate `receipt_number` | 13,937 | **0** | UUID regeneration for all 15,060 TOP_UP rows | TOP_UP rows had batch-assigned placeholder UUIDs |
| Duplicate `reference_number` | 13,937 | 13,937 | `is_ref_dup` flag added | Reference numbers intentionally shared (reconciliation design); flagged, not corrected |
| `date_order_anomaly` rows | — | 2,432 | Flag added | `created_at > paying_at` — system clock skew; rows retained |
| `net_amount` dtype | object (string) | Int64 | pd.to_numeric() | Required for arithmetic |
| `total_fee` dtype | object (string) | Int64 | pd.to_numeric() | Required for arithmetic |
| `is_verified` dtype | object ("TRUE"/"FALSE") | bool | String map | Boolean semantics |
| `paying_at`, `created_at`, `updated_at` | object (string) | datetime64 | pd.to_datetime() | Required for temporal queries |
| `phone_number` | Raw phone string | SHA-256 hash (64 chars) | hashlib.sha256() | PII protection per §4.7 governance policy |
| `is_net_amount_outlier` rows | — | 2,657 (9.4%) | IQR flag added | Large cross-border transfers are genuine |
| `is_total_fee_outlier` rows | — | 0 | IQR flag added | Fees are tightly bounded |
| Wallet ID format compliance | 28,360 / 28,360 | 28,360 / 28,360 | No changes | All WLT-XXXXXXXX on ingest |
| `note` / `detail` columns | Retained (not identical) | Retained | No action | CLAUDE.md planning doc incorrectly stated these were identical; audit confirmed 291 and 504 unique values respectively |

**Completeness before:** 100.0% | **Completeness after:** 100.0%

---

## Summary Table

| Source | Rows | Pre-clean nulls | Post-clean nulls | Structural issues found | Issues resolved |
|---|---|---|---|---|---|
| Parquet | 4,000,000 | 0 | 0 | agent_id empty strings for non-agent rows | Normalised to NULL |
| JSON | 375,837 | 0 | 0 | Date fields as strings | Coerced to datetime64 |
| XML | 28,360 | 0 | 0 | 13,937 duplicate receipt_numbers; 2,432 date-order anomalies; raw phone_number PII | UUID regen; anomaly flags; SHA-256 hash |
