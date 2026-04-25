# Data Source Appraisal: Cross-Border Partner Transactions (XML)

**Original work by:** Firas

## 1. Source & Collection
- **Origin:** Bilpay E-Wallet Platform (Indonesian fintech); Zenodo DOI: 10.5281/zenodo.17092322. Repositioned in this pipeline as a cross-border partner settlement feed from an Indonesian payment partner, with wallet IDs remapped to the `WLT-XXXXXXXX` format used by the Nigerian operator.
- **Ownership:** Bilpay / Zenodo open dataset
- **Collection mechanism:** Full-transaction export from Bilpay's batch reconciliation system (`export_type: FULL_TRANSACTION_EXPORT`)
- **Access method:** Google Drive shared folder; downloaded via `gdown`

## 2. Structure & Format
- **File format:** XML with a hierarchical namespace: `<batch> → <batch_header>` (metadata) + `<transactions> → <transaction id status>` (records)
- **Schema rigidity:** Semi-rigid — each `<transaction>` has 7 fixed child groups (`<identifiers>`, `<customer>`, `<classification>`, `<financials>`, `<channel_info>`, `<metadata>`, `<timestamps>`). Financial amounts are stored in sub-elements, not text nodes.
- **Nested structures:** Financial data is in `<financials><amount><net_amount>` and `<financials><fees>`. Transaction type is an attribute (`code=`) on the `<type>` element, not text content.
- **Encoding:** UTF-8; amounts as string integers (IDR); timestamps as `YYYY-MM-DD HH:MM:SS`

| Field (parsed) | Source path | Type after cleaning |
|---|---|---|
| transaction_id | `<transaction id>` attribute | Int64 |
| transaction_type | `<classification/type code=>` attribute | string |
| wallet_id | `<customer/wallet_id>` | string |
| net_amount | `<financials/amount/net_amount>` | Int64 (IDR) |
| total_fee | `<financials/fees/total_fee>` | Int64 (IDR) |
| is_verified | `<channel_info/is_verified>` | bool |
| receipt_number | `<identifiers/receipt_number>` | string (UUID) |
| paying_at, created_at, updated_at | `<timestamps/*>` | datetime64 |

## 3. Volume & Velocity
- **Current size:** 28,360 records; 55.8 MB on disk; 479 unique wallets
- **Growth rate:** Static export (July 2024 – January 2025, 6-month window)
- **Update frequency:** One-time batch export; in production would receive daily settlement files
- **Latency requirements:** Settlement feeds typically have T+1 day latency — batch is appropriate

## 4. Quality Assessment
- **Completeness %:** 100% after parsing (zero nulls when XML is correctly parsed with the nested extractor). The flat child-element extractor produces 26 populated columns.
- **Accuracy evidence:** 28,360 records match the `record_count` metadata header exactly. All 28,360 wallet_ids match `WLT-XXXXXXXX`. 479 unique wallets match the `total_wallets` header.
- **Consistency issues:**
  - `receipt_number`: 13,937 duplicates — all 15,060 TOP_UP rows share batch-generated placeholder UUIDs. Corrected by regenerating UUIDs in `clean_xml.py`.
  - `reference_number`: 13,937 duplicates — same root cause. Flagged with `is_ref_dup` boolean; not corrected (reference numbers are used for external reconciliation).
  - `created_at > paying_at`: 2,432 rows — system clock skew at the point of sale. Flagged with `date_order_anomaly`; rows retained.
  - `note` and `detail`: Both non-empty and distinct (291 and 504 unique values respectively). Both retained in the cleaned output.

## 5. Risks & Limitations
- **Biases:** The Bilpay source uses Indonesian Rupiah (IDR) with no currency conversion to NGN in the current pipeline. Cross-source amount comparisons between the XML and Parquet fact tables require an exchange rate layer not implemented at this scope.
- **Missing patterns:** No merchant-level data (only category codes). No reversal/chargeback linkage for REFUND transactions.
- **Ethical/legal concerns:** `phone_number` is present and hashed with SHA-256 in `clean_xml.py`. The hash is irreversible (no salt by design — consistent with the academic scope where reversibility is not required; a production system would use HMAC-SHA256 with a server-side secret).
- **Schema drift risks:** Bilpay updates schema version 2.1 periodically. The nested XML parser (`_parse_tx` in `ingest_xml.py`) uses explicit XPath paths; any tag rename would cause silent `None` values. The validation assertions (`record_count` match, `wallet_count` match) would catch complete failures but not partial field renames.
