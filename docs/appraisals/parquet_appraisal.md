# Data Source Appraisal: Nigerian Mobile Money Transactions (Parquet)

**Original work by:** Nadine + Patrick

## 1. Source & Collection
- **Origin:** Hugging Face dataset `electricsheepafrica/africa-financial-inclusion-nigeria` (published 2025)
- **Ownership:** Electric Sheep Africa; open dataset, no commercial restrictions
- **Collection mechanism:** Synthetic generation seeded from real financial-inclusion survey data; deterministic and reproducible
- **Access method:** Direct download from HuggingFace Hub via `pd.read_parquet("hf://...")` then persisted to Google Drive at `raw_mobile_money.parquet` (237 MB compressed)

## 2. Structure & Format
- **File format:** Apache Parquet (columnar, Snappy-compressed)
- **Schema rigidity:** Fixed — 13 columns, no optional fields
- **Nested structures:** None; fully flat schema
- **Encoding:** UTF-8 strings; datetime64[ns] for timestamps; bool for flag columns

| Column | Type | Description |
|---|---|---|
| transaction_id | object | Unique transaction identifier |
| wallet_id | object | `WLT-XXXXXXXX` format |
| timestamp | datetime64[ns] | Transaction timestamp |
| transaction_type | object | airtime, p2p_send, p2p_receive, billpay, cashin, cashout, data |
| amount_ngn | float64 | Transaction amount (₦) |
| fee_ngn | float64 | Fee charged (₦) |
| balance_after_ngn | float64 | Wallet balance after transaction (₦) |
| agent_id | object | Agent ID (cashin/cashout only) |
| channel | object | ussd, app, agent, web |
| device_os | object | Device operating system |
| kyc_tier | object | tier1, tier2, tier3 |
| fraud_flag | bool | True if transaction flagged as fraud |
| churn_30d | bool | True if wallet churned within 30 days |

## 3. Volume & Velocity
- **Current size:** 4,000,000 rows × 13 columns; 237 MB compressed, ~2 GB uncompressed in Postgres
- **Growth rate:** Static (academic export — no future updates)
- **Update frequency:** One-time batch load
- **Latency requirements:** None — batch analytical workload

## 4. Quality Assessment
- **Completeness %:** 100% — zero nulls across all 13 columns (confirmed by audit)
- **Accuracy evidence:** All wallet_ids match `WLT-XXXXXXXX` (4,000,000/4,000,000). No duplicate `transaction_id`. Timestamp range is internally consistent (Jan–Jun 2024).
- **Consistency issues:** `agent_id` is an empty string (not NULL) for non-cashin/cashout transactions — corrected in cleaning.
- **Note on raw vs stg files:** `stg_mobile_money.parquet` is byte-identical to `raw_mobile_money.parquet` except for a column rename (`timestamp` → `txn_timestamp`). The staging step was a no-op. Raw is used as the single source.

## 5. Risks & Limitations
- **Biases:** Synthetic data generator may not perfectly replicate the tail-distribution of real Nigerian mobile money (e.g., very large transactions, seasonal spikes during Eid). Any model trained on this data should be validated on real data before production use.
- **Missing patterns:** No geographic (state-level) breakdown, no merchant category codes — limits fraud pattern analysis to channel and transaction-type dimensions.
- **Ethical/legal concerns:** No real PII present. Wallet IDs are synthetic. Safe to share openly.
- **Schema drift risks:** None — static dataset. In a production scenario, the HuggingFace dataset owner could add or rename columns; ingest validation (`REQUIRED_COLS` assertion) would catch this immediately.
