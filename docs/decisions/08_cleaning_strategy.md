# Cleaning Strategy — Per-Source Rules

## Universal rules (applied to all three sources)

### Missing values — FLAG, do not silently impute
- Columns with >50% missing: DROPPED (documented in before/after table)
- Columns with 5–50% missing: sibling `<column>_is_missing` boolean flag added; original value retained
- Columns with <5% missing: IMPUTED with median (numeric) or mode (categorical), logged
- **Rationale:** Silent imputation introduces bias toward the imputed value and destroys the information that the field was unknown — especially critical for PII fields like `phone_number`.

### Outliers — IQR-based flagging, not removal
- For every numeric financial column, compute IQR. Values outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]` receive a boolean flag (`is_amount_outlier`, `is_fee_outlier`, etc.).
- **Outlier rows are never removed.** Large transactions are genuine (wholesale deposits, cross-border remittances) and removing them would bias all downstream analytics.
- **Rationale:** In financial data, outliers are often the most analytically interesting records.

### Validation rules (enforced before every DB commit)
All `src/storage/load_*.py` modules assert before committing:
1. Primary key uniqueness (`transaction_id`, `wallet_id` in profile collection)
2. Foreign key format (`wallet_id` matches regex `^WLT-\d{8}$`)
3. Value range: all amount columns `>= 0`
4. Temporal sanity: `paying_at <= updated_at` (flagged, not dropped)
5. Enum conformance: `transaction_type` in known set

---

## Per-source specifics

### Parquet (Nigerian Mobile Money)
- **Source quality:** Excellent. Zero nulls, zero duplicates on ingest.
- **Type coercions:** `timestamp` → `datetime64[ns]` (already correct); `fraud_flag`, `churn_30d` → `bool`
- **agent_id normalisation:** Empty string → `None` for non-cashin/cashout transaction types (agent_id is meaningless for those types)
- **Outlier flags added:** `is_amount_ngn_outlier`, `is_fee_ngn_outlier`, `is_balance_after_ngn_outlier`
- **Note:** `stg_mobile_money.parquet` is byte-identical to `raw_mobile_money.parquet` except for a column rename (`timestamp` → `txn_timestamp`). The stg file is not used; raw is the primary source.

### JSON (Customer Profiles)
- **Source quality:** Excellent. Zero nulls, zero duplicate wallet_ids, 375,837 records matching the metadata header.
- **Type coercions:** `date_of_birth`, `registration_date` → `datetime64`
- **Normalisation:** All categorical strings lowercased (`account_status`, `referral_source`, `support_tier`, `gender`, `preferred_language`, `notification_preferences`)
- **Age anomaly flag:** `is_age_anomaly = True` where age < 10 or age > 120 (none found in current data)
- **No phone_number present** in JSON profiles; SHA-256 hashing applies only to the XML source.

### XML (Cross-border partner transactions)
- **Source quality:** Moderate. All 15,060 TOP_UP rows have duplicate `receipt_number` values (batch-generated placeholder UUIDs from the Bilpay system). 2,432 date-order anomalies.
- **CORRECTION from planning documents:** `note` and `detail` columns are NOT identical (291 and 504 unique values respectively). Both are retained.
- **Cleaning actions (in order):**
  1. Type casts: amounts → `Int64`, `is_verified` → `bool`, timestamps → `datetime64`, `transaction_id` → `Int64`
  2. UUID regeneration: all 15,060 TOP_UP `receipt_number` values replaced with new `uuid.uuid4()` values; uniqueness verified (0 dups remain)
  3. `is_ref_dup` flag: 15,060 rows share a `reference_number`
  4. `date_order_anomaly` flag: 2,432 rows where `created_at > paying_at`
  5. `phone_number` SHA-256 hashed
  6. IQR outlier flags: `is_net_amount_outlier`, `is_total_fee_outlier`
