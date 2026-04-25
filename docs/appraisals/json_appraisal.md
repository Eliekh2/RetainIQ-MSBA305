# Data Source Appraisal: Customer Profiles (JSON)

**Original work by:** Jad Badran + Elie Estephan

## 1. Source & Collection
- **Origin:** Team-generated synthetic dataset (`generate_customer_profiles.py`, GitHub: `feature/customer-profiles`)
- **Ownership:** Team-generated; no external copyright
- **Collection mechanism:** Deterministic synthetic generation seeded per `wallet_id` extracted from `raw_mobile_money.parquet` (375,837 unique wallets). Fully reproducible with the same seed.
- **Access method:** Google Drive shared folder; downloaded via `gdown`

## 2. Structure & Format
- **File format:** JSON with metadata wrapper object (`obj['data']` contains the records array); NOT NDJSON
- **Schema rigidity:** Fixed 14 flat fields; no optional fields in current version
- **Nested structures:** None — fully flat after extraction from the wrapper
- **Encoding:** UTF-8; date fields as ISO-8601 strings (`YYYY-MM-DD`)

| Column | Type | Description |
|---|---|---|
| wallet_id | string | `WLT-XXXXXXXX` format — join key |
| full_name | string | Customer name |
| date_of_birth | string → datetime | Date of birth |
| age | int | Age in years (18–65) |
| gender | string | Male / Female |
| state | string | Nigerian state |
| city | string | City within state |
| registration_date | string → datetime | Account registration date |
| account_status | string | active / dormant / suspended |
| referral_source | string | How customer was acquired |
| preferred_language | string | English / Hausa / Yoruba / Igbo / Pidgin |
| notification_preferences | string | Notification channel preference |
| linked_bank | string | Partner bank |
| support_tier | string | standard / silver / gold |

## 3. Volume & Velocity
- **Current size:** 375,837 records; 183 MB on disk
- **Growth rate:** Static — number of profiles equals number of unique wallets in the parquet source
- **Update frequency:** One-time batch load; in production would update nightly as new wallets register
- **Latency requirements:** None — batch analytical workload

## 4. Quality Assessment
- **Completeness %:** 100% — zero nulls across all 14 columns (confirmed by audit)
- **Accuracy evidence:** 375,837 unique wallet_ids, all matching `WLT-XXXXXXXX`. Count matches `records_total` in the JSON metadata header (375,837). No duplicate wallet_ids.
- **Consistency issues:** None found. Date fields are consistently formatted. Categorical values are consistent within each column.
- **Age distribution:** Uniform 18–65 (by design of the synthetic generator). Real-world age distribution would be right-skewed toward younger adults.

## 5. Risks & Limitations
- **Biases:** Uniform age and near-equal gender split are artifacts of synthetic generation. Real Nigerian mobile-money demographics skew younger and male (GSMA Financial Inclusion data, 2024).
- **Missing patterns:** No income data, no transaction history embedded in profiles (by design — kept in the transactional source). No device model or OS (that information is in the Parquet source).
- **Ethical/legal concerns:** No real PII. Names are synthetic. Wallet IDs are synthetic. `date_of_birth` is synthetic; if real DOBs were present they would require NDPR (Nigeria Data Protection Regulation) compliance.
- **Schema drift risks:** Team may add new KYC attributes in future iterations; the flat DataFrame normalisation would pick them up automatically, but MongoDB index coverage would need updating.
