# RetainIQ Pipeline — MSBA 305

**Course:** AUB MSBA 305 — Data Processing Framework, Spring 2025/2026 | Dr. Ahmad El-Hajj

Multi-source data pipeline for digital wallet customer churn analytics. Ingests Nigerian mobile money transactions (Parquet, 4M rows), customer profiles (JSON, 375K documents), and cross-border partner settlements (XML, 28K records), cleans and integrates them into a unified analytical layer, and produces five business-oriented SQL queries with a full visualization report.

---

## Setup

### Prerequisites
- Python 3.11.9 (`py -3.11`)

### Install dependencies
```bash
py -3.11 -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Download raw data
```bash
python download_data.py
```
This downloads the three raw source files from the shared Google Drive folder into `data/raw/`. It takes a few minutes depending on your connection.

### Database connections
**No configuration needed.** Both databases (Neon Postgres and MongoDB Atlas) are live cloud instances. Their connection strings are hardcoded as defaults in `src/config.py` — the notebooks connect automatically without any `.env` file or local database setup.

---

## Running the Project

Run the notebooks in order — each one is self-contained and builds on the previous:

| Notebook | What it does | Rubric |
|---|---|---|
| `01_parquet_ingestion_eda.ipynb` | Ingest + clean Nigerian mobile money transactions (Parquet) | §4.1, §4.3 |
| `02_json_ingestion_eda.ipynb` | Ingest + clean customer profiles (JSON) | §4.1, §4.3 |
| `03_xml_ingestion_eda.ipynb` | Ingest + clean cross-border settlements (XML) | §4.1, §4.3 |
| `04_storage_load.ipynb` | Load all three sources into Postgres and MongoDB | §4.2 |
| `05_integration_join.ipynb` | Build unified dimension table (`dim_unified_wallet`) | §4.2, §4.4 |
| `06_analytical_queries.ipynb` | Run 5 analytical SQL queries + MongoDB aggregation | §4.5 |
| `07_visualization_report.ipynb` | EDA visualization report (8 charts) | §4.6 |

HTML exports of notebooks 06 and 07 are committed to the repo if you prefer to view results without running.

---

## Deliverables

| Item | Location |
|---|---|
| Architecture Report | `docs/architecture_report.docx` |
| AI Usage Log | `docs/ai_usage_log.md` |
| Data Governance Policy | `docs/governance.md` |
| Data Quality Report | `docs/data_quality_report.md` |
| SQL Schema | `sql/schema.sql` |
| Analytical Queries | `sql/queries/` |

---

## Team

| Member | Contribution |
|---|---|
| Elie Khairallah | Team coordination, pipeline consolidation, storage design, integration, architecture report |
| Nadine Daaboul + Patrick Daou | Data acquisition (Parquet), ingestion, cleaning, EDA, source appraisals, visualization report |
| Jad Badran + Elie Estephan | Data acquisition (JSON), ingestion, cleaning, EDA, source appraisals, presentation |
| Firas Harb | Data acquisition (XML), ingestion, cleaning, EDA, source appraisals, analytical queries |
