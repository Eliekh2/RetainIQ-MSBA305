# Decision: Neon PostgreSQL for structured transactional data

## Decision
Use Neon (serverless cloud-hosted PostgreSQL) as the relational store for:
- The Nigerian Mobile Money transaction fact table (stratified 500K-row sample)
- The XML-derived cross-border partner transaction fact table
- Wallet-level aggregation and unified dimension tables

## Alternatives considered
1. **MongoDB for everything**
2. **MySQL (Oracle Cloud free tier)**
3. **Local SQLite**

## Why rejected
1. **MongoDB for everything:** Our primary analytical queries require multi-source JOINs (transactions × customer profiles × branch interactions). MongoDB's `$lookup` is verbose and slower than native SQL JOINs for our access patterns. Our transaction fact tables have a fixed schema post-cleaning, eliminating MongoDB's schema-flexibility advantage. Keeping only genuinely document-shaped data in Mongo is a stronger architectural fit.
2. **MySQL (Oracle Cloud free tier):** MySQL's JSON handling and window function support is weaker than Postgres. Oracle Cloud free tier has a 20 GB storage allowance but requires credit card verification and complex activation. Neon's free tier requires no credit card and its scale-to-zero serverless model means we don't burn compute hours while idle.
3. **Local SQLite:** No network accessibility — the professor cannot run queries against a local database. SQLite's limited concurrency and lack of server-side features (advanced indexing, partial indexes) would be a regression from what the rubric requires.

## Trade-offs accepted
- **0.5 GB free-tier storage cap** — addressed by loading a stratified 500K-row sample of the Parquet source (see `05_parquet_sampling.md`) rather than all 4M rows. The full dataset remains as a file artifact.
- **Network latency** — Neon is cloud-hosted, so local querying has ~50–150 ms RTT. Mitigated by connection pooling and batching reads in notebooks.
- **Scale-to-zero cold starts** — ~300 ms on the first query after idle. Acceptable for academic and analytical use.
