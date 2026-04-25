# Rubric Compliance Report — RetainIQ Pipeline (MSBA 305)

> This document maps every rubric requirement to what was delivered in the project.
> It is intended for inclusion in a course-context repository so that lecture-aware
> question generators can produce more targeted follow-up questions.
> Last updated: April 2026.

---

## Project Identity

| Field | Value |
|---|---|
| Course | MSBA 305 — Data Processing Framework, Spring 2025/2026 |
| Instructor | Dr. Ahmad El-Hajj, AUB |
| Team size | 6 (written approval on file — rubric max is 5) |
| Submission | Architecture Report (docx) + 7 Jupyter notebooks + GitHub repo |
| Repository | https://github.com/Eliekh2/RetainIQ-MSBA305 |
| Business domain | Digital wallet churn analytics, Nigerian mobile money operator |

---

## §4.1 — Data Ingestion

### What the rubric requires
Ingest data from at least two distinct sources with different formats. Demonstrate understanding of format-specific parsing. Document source provenance and collection mechanism.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Multiple distinct source formats | **Delivered — 3 formats** | Apache Parquet, JSON, XML |
| Format-specific ingestion logic | **Delivered** | `src/ingestion/ingest_parquet.py`, `ingest_json.py`, `ingest_xml.py` — each uses different parsing libraries and strategies |
| Source provenance documented | **Delivered** | `docs/appraisals/parquet_appraisal.md`, `json_appraisal.md`, `xml_appraisal.md` — each covers origin, ownership, collection mechanism, access method |
| Ingestion in Jupyter notebooks | **Delivered** | Notebooks 01, 02, 03 — one per source, with EDA |
| Volume documented | **Delivered** | Parquet: 4M rows / 237 MB; JSON: 375,837 docs / 183 MB; XML: 28,360 records / 55 MB |

### Source summary

| Source | Format | Origin | Volume | Join key |
|---|---|---|---|---|
| Nigerian Mobile Money | Apache Parquet | Hugging Face (electricsheepafrica/africa-financial-inclusion-nigeria) | 4,000,000 rows | `wallet_id` |
| Customer Profiles | JSON | Synthetic generator, stored on Google Drive | 375,837 documents | `wallet_id` |
| Cross-Border Settlements | XML | Bilpay / Zenodo DOI: 10.5281/zenodo.17092322 | 28,360 records | `wallet_id` (remapped) |

### Known gaps / honest notes
- The XML source is an Indonesian fintech dataset repositioned as a cross-border partner feed. Currency (IDR) is not converted to NGN — documented as a known scope limitation.
- Raw files exceed GitHub's 100 MB per-file limit and are hosted on Google Drive, downloaded via `download_data.py`.

---

## §4.2 — Storage

### What the rubric requires
Store data in at least one structured database. Justify the storage choice. Demonstrate schema design. Use indexes appropriately.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Structured relational database | **Delivered** | Neon Postgres (cloud, free tier, 0.5 GB) |
| Document database | **Delivered (bonus)** | MongoDB Atlas M0 (cloud, free tier, 512 MB) |
| Schema design documented | **Delivered** | `sql/schema.sql` — 5 tables with PK, FK references, constraints |
| Indexes | **Delivered** | `sql/indexes.sql` — B-tree on `wallet_id` and `timestamp`; two partial indexes on `fraud_flag` and `churn_30d` |
| Storage choice justified | **Delivered** | `docs/decisions/01_storage_postgres.md`, `02_storage_mongodb.md`, `07_integration_pattern.md` |
| Cloud access for professor | **Delivered** | Both DBs on free cloud tiers; credentials hardcoded as fallback defaults in `src/config.py` |

### Schema overview (Postgres)

| Table | Rows | Type | Primary source |
|---|---|---|---|
| `fact_mobile_money_tx` | 500,000 | Fact | Parquet (stratified sample) |
| `fact_xml_transactions` | 28,360 | Fact | XML |
| `dim_wallet_agg_mm` | 375,837 | Dimension/Aggregate | Parquet |
| `dim_wallet_agg_xml` | 479 | Dimension/Aggregate | XML |
| `dim_unified_wallet` | 375,837 | Denormalised Integration | Mongo + Postgres ETL |

### Key design decisions
- **Stratified 500K sample** instead of full 4M rows — Neon free tier 0.5 GB cap.
- **Polyglot persistence** — MongoDB for document-centric profiles, Postgres for relational facts and dimensions.
- **Mongo → Postgres ETL** (not application-level joins) — allows all 5 analytical queries to run in pure SQL with JOIN to `dim_unified_wallet`.

---

## §4.3 — Data Cleaning

### What the rubric requires
Document data quality issues found. Apply cleaning transformations. Produce a before/after quality report. Justify every cleaning decision.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Before/after quality statistics | **Delivered** | `docs/data_quality_report.md` — per-source table with row counts, null counts, dtype changes, structural issues |
| Cleaning decisions justified | **Delivered** | `docs/decisions/08_cleaning_strategy.md` — universal rules + per-source specifics |
| No silent imputation | **Delivered** | All nulls flagged (boolean columns), never silently replaced |
| Outlier handling | **Delivered** | IQR-based flagging; original columns untouched |
| PII handling | **Delivered** | SHA-256 hash on `phone_number` (XML); no phone numbers in JSON |

### Cleaning actions by source

**Parquet:**
- `agent_id` empty strings → NULL for non-cashin/cashout rows (semantic correctness)
- 3 IQR outlier flag columns added: `is_amount_ngn_outlier`, `is_fee_ngn_outlier`, `is_balance_after_ngn_outlier`
- Stratified sample to 500K rows (storage constraint, not a data quality action)

**JSON:**
- `date_of_birth`, `registration_date` → `datetime64` (type coercion)
- 6 categorical columns lowercased (consistent groupby behaviour)
- `is_age_anomaly` flag added (no anomalies found; flag retained for production)

**XML:**
- 13,937 duplicate `receipt_number` values → UUID regeneration (batch placeholder pattern confirmed)
- `is_ref_dup` flag on 13,937 `reference_number` duplicates (external reconciliation field — not corrected)
- 2,432 `date_order_anomaly` flags (`created_at > paying_at` — system clock skew, rows retained)
- SHA-256 hash applied to `phone_number`
- Amounts (`net_amount`, `total_fee`) → `Int64` from string
- Timestamps → `datetime64`
- 2 IQR outlier flag columns: `is_net_amount_outlier`, `is_total_fee_outlier`

### Key principle
**Flag, never delete.** No row was removed in any cleaning step across all three sources. Financial records must remain auditable and complete; removing rows is reserved for provably false data (instrument error), which was not found.

---

## §4.4 — Processing & Integration

### What the rubric requires
Apply transformations beyond basic cleaning. Integrate multiple data sources. Justify integration design.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Cross-source integration | **Delivered** | `dim_unified_wallet` — 375,837 rows, one per wallet, combining Mongo profiles + Parquet aggregates + XML presence flag |
| Integration design justified | **Delivered** | `docs/decisions/07_integration_pattern.md` — Mongo→Postgres ETL vs application-level joins vs JSONB |
| Derived metrics | **Delivered** | `dominant_channel`, `dominant_tx_type` via `MODE() WITHIN GROUP`; `total_volume_ngn`, `total_fees_ngn`, `avg_tx_amount`, `tx_count`, `first_tx_date`, `last_tx_date` |
| Notebook coverage | **Delivered** | Notebook 05 (`05_integration_join.ipynb`) runs and verifies the full ETL |
| Field mapping documented | **Delivered** | Section 4.4 of `docs/architecture_report.docx` contains a 25-row field mapping table showing every `dim_unified_wallet` column's source |

### Integration architecture
```
MongoDB Atlas (customer_profiles)
        ↓ pymongo pull (375,837 docs)
        ↓
Postgres (dim_wallet_agg_mm)   ← Parquet aggregates per wallet
Postgres (dim_wallet_agg_xml)  ← XML presence check (boolean only)
        ↓ pandas merge on wallet_id
        ↓
Postgres (dim_unified_wallet)  ← upsert via SQLAlchemy
```

### Why XML amounts are not in the unified view
The XML source is denominated in IDR; Parquet amounts are in NGN. Merging them without an FX rate would produce a meaningless mixed-currency aggregate. `has_xml_activity BOOLEAN` is the only XML-derived column in `dim_unified_wallet`. This is explicitly documented as a known scope limitation.

---

## §4.5 — Querying

### What the rubric requires
Write and execute meaningful analytical queries. Demonstrate SQL capability (aggregation, joins, window functions). Use the databases built in §4.2.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Multiple analytical queries | **Delivered — 5 SQL + 1 MQL** | `sql/queries/q1_*.sql` through `q5_*.sql`; MongoDB Q3 in `src/queries/analytical_queries.py` |
| Aggregation | **Delivered** | Q1 (monthly totals), Q2 (churn rate by segment), Q3 (profile demographic distribution) |
| JOIN | **Delivered** | Q4 joins `fact_mobile_money_tx` to `dim_unified_wallet` on `wallet_id` |
| Window functions | **Delivered** | Q5 uses `LAG()` partitioned by `wallet_id` ordered by month |
| CTE | **Delivered** | Q5 uses two CTEs (`monthly`, `growth`) |
| Safe division | **Delivered** | Q2 uses `NULLIF(denominator, 0)` + `::NUMERIC` cast |
| MongoDB aggregation | **Delivered** | Q3 MQL `$group` pipeline on `customer_profiles` collection |
| Executed and results shown | **Delivered** | Notebook 06 runs all 5 queries; HTML export committed |

### Query index

| Query | Business question | SQL features used |
|---|---|---|
| Q1 | Monthly platform volume growth | `DATE_TRUNC`, `SUM`, `AVG`, `GROUP BY`, `ORDER BY` |
| Q2 | Churn rate by KYC tier and channel | `CASE WHEN`, `NULLIF`, `ROUND`, conditional aggregation, `::NUMERIC` |
| Q3 | Customer demographic profile distribution | `COUNT`, `AVG`, window `SUM() OVER ()`, `LIMIT` / MQL `$group` |
| Q4 | Top 10 wallets by volume with profile enrichment | Multi-table `JOIN`, `MAX(CASE WHEN)`, `GROUP BY` multiple columns |
| Q5 | Month-over-month volume growth, top 5 wallets | CTEs, `LAG()` window function, `NULLIF`, `ROUND`, `PARTITION BY` |

---

## §4.6 — Visualization

### What the rubric requires
Produce visualizations that communicate analytical findings. Justify chart type choices.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Multiple charts | **Delivered — 8 charts** | Notebook 07 (`07_visualization_report.ipynb`) |
| Chart types varied | **Delivered** | Line, dual-axis combo, grouped bar, pie, scatter |
| HTML export | **Delivered** | `notebooks/07_visualization_report.html` committed to repo |
| Findings communicated | **Delivered** | Each chart has a title, axis labels, and a markdown interpretation cell |

### Chart index

| # | Chart | Type | Question answered |
|---|---|---|---|
| 1 | Monthly transaction volume + count | Dual-axis line/bar | Is the platform growing? |
| 2 | Churn rate by KYC tier × channel | Grouped bar | Which segments churn most? |
| 3 | Transaction type distribution | Pie | What do wallets use the platform for? |
| 4 | Fraud flag rate by channel | Bar | Which channels have highest fraud concentration? |
| 5 | Wallet registration recency distribution | Histogram | How old is the customer base? |
| 6 | Top 10 wallets by transaction count | Horizontal bar | Who are the power users? |
| 7 | Transaction fee vs amount | Scatter | What is the fee structure shape? |
| 8 | Churn vs transaction count | Scatter | Do high-activity wallets churn less? |

---

## §4.7 — Data Governance

### What the rubric requires
Define a data governance policy. Cover data classification, access control, retention, and ethical considerations. Document PII handling.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Data classification policy | **Delivered** | `docs/governance.md` §1 — 4 tiers: PII-Sensitive, PII-Confidential, Confidential, Internal |
| Access control | **Delivered** | `docs/governance.md` §2 — 3 roles: `etl_loader`, `analyst`, `admin`; PII column restriction via view |
| Data retention | **Delivered** | `docs/governance.md` §3 — 7-year retention per Nigerian BOFIA 2020 §22 and NDPR |
| Backup & recovery | **Delivered** | `docs/governance.md` §4 — RPO/RTO for Neon (6h/1h), Atlas (24h/2h), Drive (real-time), GitHub (per-commit) |
| Ethical considerations | **Delivered** | `docs/governance.md` §6 — synthetic data bias, gender/age distribution limitations, IDR/NGN scope, SHA-256 design |
| PII handling | **Delivered** | SHA-256 hash on `phone_number` in `clean_xml.py`; `full_name` and `date_of_birth` in Mongo — no hashing (synthetic, treated as confidential) |
| Deletion procedure | **Delivered** | Right-to-erasure workflow documented: delete Mongo doc, anonymise Postgres rows with tombstone hash, log event |

### Regulatory grounding

| Regulation | Application in this project |
|---|---|
| Nigerian BOFIA 2020 §22 | 7-year retention for financial transaction records |
| NDPR (Nigeria Data Protection Regulation) | PII handling, retention for profile data, right-to-erasure workflow |
| Academic integrity (rubric §7) | AI usage log — all 14 interactions documented |

---

## §7 — AI Usage Log (Rubric Requirement)

### What the rubric requires
Document every meaningful AI interaction: the prompt, the response summary, how it was incorporated, and modifications made. Warning against direct copy-pasting without understanding.

### What was delivered

| Requirement | Status | Detail |
|---|---|---|
| Standalone log file | **Delivered** | `docs/ai_usage_log.md` — 14 entries |
| Report section | **Delivered** | `docs/architecture_report.docx` §7 — 2-para preamble, 14-row summary table, 4 representative full entries, pointer to canonical file |
| Prompt documented | **Delivered** | Every entry includes the exact or reconstructed prompt |
| Response summary | **Delivered** | Every entry explains what the AI explained (not what it produced) |
| How incorporated | **Delivered** | Every entry describes what the team member did with the explanation |
| Modifications | **Delivered** | Every entry shows adaptation, rejection, or improvement over the AI suggestion |
| Rubric coverage | **Delivered** | Entries span §4.1 through §4.7 plus cross-cutting debugging |

### Coverage by rubric section

| Rubric § | Entries |
|---|---|
| 4.1 Ingestion | 1, 2 |
| 4.2 Storage | 3, 4, 5 |
| 4.3 Cleaning | 6, 7, 8 |
| 4.4 Processing | 9 |
| 4.5 Querying | 10, 11 |
| 4.6 Visualization | 12 |
| 4.7 Governance | 13 |
| Cross-cutting | 14 |

---

## Architecture Report (65% of grade)

### What the rubric requires
A structured Word document covering the full pipeline design, decisions, and findings.

### What was delivered

`docs/architecture_report.docx` — structured as follows:

| Section | Content |
|---|---|
| 1. Executive Summary | Project overview, business context, three-source rationale |
| 2. Data Sources | Per-source description, format, volume, provenance |
| 3. Storage Architecture | Schema diagram, table descriptions, index design, polyglot justification |
| 4. Processing Pipeline | Cleaning strategy, integration design, field mapping table (25 rows × 5 cols) |
| 5. Analytical Queries | All 5 queries with business questions and SQL features used |
| 6. References | Dataset citations, regulatory references, tool citations |
| 7. AI Usage Log | Preamble, 14-row summary table, 4 representative full entries, pointer to canonical log |

---

## Decision Records (Architecture Decision Records)

All major design choices are documented in `docs/decisions/`:

| File | Decision |
|---|---|
| `01_storage_postgres.md` | Why Neon Postgres over local SQLite |
| `02_storage_mongodb.md` | Why MongoDB Atlas over Postgres JSONB for profiles |
| `03_ingestion_batch.md` | Why batch ingestion over streaming (no real-time SLA) |
| `04_processing_pandas.md` | Why local pandas over PySpark (900K rows fits in memory) |
| `05_parquet_sampling.md` | Why stratified 500K sample — Neon storage constraint |
| `06_cloud_vs_local.md` | Cloud databases for professor access, local processing |
| `07_integration_pattern.md` | Mongo→Postgres ETL vs application-level joins |
| `08_cleaning_strategy.md` | Universal cleaning rules (flag vs remove, IQR vs z-score, imputation thresholds) |

---

## Known Limitations (Honest Assessment)

| Limitation | Impact | Documented in |
|---|---|---|
| XML amounts in IDR, not converted to NGN | No cross-source financial comparisons; IDR amounts isolated in `fact_xml_transactions` and `dim_wallet_agg_xml` — not mixed into any NGN aggregate | `docs/governance.md` §6, `docs/appraisals/xml_appraisal.md` §5 |
| Stratified sample (500K of 4M rows) | Q1–Q5 results are estimates, not full-population statistics | `docs/decisions/05_parquet_sampling.md` |
| Synthetic data | Fraud and churn signals are probabilistically generated, not observed; demographic distributions are not representative of real Nigerian mobile-money users | `docs/governance.md` §6 |
| Single admin credential | Production would enforce `etl_loader` / `analyst` role separation with PII view | `docs/governance.md` §2 |
| Static data, no streaming | Pipeline is batch-only; a production system would add a streaming layer for real-time churn signals | `docs/decisions/03_ingestion_batch.md` |
| SHA-256 without salt | Vulnerable to rainbow table attacks on the predictable phone number space; HMAC-SHA256 is the production fix | `docs/appraisals/xml_appraisal.md` §5 |

---

## Repository Structure

```
retainiq-pipeline/
├── src/
│   ├── ingestion/          ingest_parquet.py, ingest_json.py, ingest_xml.py
│   ├── cleaning/           clean_parquet.py, clean_json.py, clean_xml.py
│   ├── storage/            postgres_setup.py, mongo_setup.py, load_*.py (3 loaders)
│   ├── integration/        build_unified_view.py
│   ├── queries/            analytical_queries.py
│   ├── config.py           DB connection factories (credentials hardcoded as defaults)
│   └── logging_setup.py
├── notebooks/
│   ├── 01_parquet_ingestion_eda.ipynb
│   ├── 02_json_ingestion_eda.ipynb
│   ├── 03_xml_ingestion_eda.ipynb
│   ├── 04_storage_load.ipynb
│   ├── 05_integration_join.ipynb
│   ├── 06_analytical_queries.ipynb
│   ├── 06_analytical_queries.html
│   ├── 07_visualization_report.ipynb
│   └── 07_visualization_report.html
├── sql/
│   ├── schema.sql          5-table Postgres schema
│   ├── indexes.sql         B-tree + partial indexes
│   └── queries/            q1_*.sql through q5_*.sql
├── docs/
│   ├── architecture_report.docx
│   ├── governance.md
│   ├── data_quality_report.md
│   ├── ai_usage_log.md     (14-entry canonical AI log)
│   ├── decisions/          08 ADR files
│   └── appraisals/         parquet_appraisal.md, json_appraisal.md, xml_appraisal.md
├── data/samples/           Small git-tracked samples (parquet CSV, xml CSV, json)
├── tests/                  test_config.py, test_ingestion.py, test_queries.py
├── download_data.py        Google Drive → data/raw/
├── requirements.txt        21 Python packages
└── README.md
```

---

## Overall Rubric Compliance Summary

| Section | Weight (indicative) | Status |
|---|---|---|
| §4.1 Data Ingestion | High | Fully delivered — 3 sources, 3 formats, documented |
| §4.2 Storage | High | Fully delivered — Postgres + MongoDB, schema, indexes, cloud access |
| §4.3 Cleaning | High | Fully delivered — quality report, flagging strategy, PII hashing |
| §4.4 Processing | High | Fully delivered — unified view, field mapping, integration design |
| §4.5 Querying | High | Fully delivered — 5 SQL queries + 1 MQL, window functions, CTEs |
| §4.6 Visualization | Medium | Fully delivered — 8 charts, HTML exports |
| §4.7 Governance | Medium | Fully delivered — classification, roles, retention, ethics |
| Architecture Report | 65% of grade | Delivered — all sections, field mapping table, AI log section |
| AI Usage Log | Required | Delivered — 14 entries, learning-journal tone, spans all sections |
| Decision Records | Supplementary | Delivered — 8 ADR files |
