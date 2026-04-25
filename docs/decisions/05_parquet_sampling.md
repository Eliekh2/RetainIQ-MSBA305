# Decision: Load stratified 500K-row sample of Parquet into Postgres

## Decision
The full 4M-row Parquet source is kept as a file artifact (`data/raw/raw_mobile_money.parquet`). A stratified random sample of ~500,000 rows is loaded into Neon Postgres for analytical queries.

**Stratification keys:** `(transaction_type, churn_30d, fraud_flag)` — preserves the distribution of rare events (6% churn, 1.5% fraud) across the sample.

**Reproducibility:** `random_state=42` — re-running the sampling script always produces the same sample.

## Alternatives considered
1. **Load the full 4M rows into Postgres**
2. **Load into a larger paid DB tier**
3. **Keep everything in Parquet files, no DB**

## Why rejected
1. **Full 4M rows:** Uncompressed in Postgres, 4M Parquet rows become ~2 GB. This exceeds the Neon free tier cap of 0.5 GB. Upgrading to Neon's Launch plan ($5/month minimum) is out of scope for an academic project.
2. **Paid tier:** Not needed. A 500K-row stratified sample preserves the full statistical structure of the data for every analytical query we need to run. Paying for infrastructure our workload doesn't require is bad architecture.
3. **No DB:** Rubric §4.2 requires a database storage decision with indexing and partitioning strategy. Parquet-on-disk cannot satisfy this requirement.

## Trade-offs accepted
- **Sampling error on rare-event queries** — mitigated by stratifying on the rare events themselves. Fraud prevalence in sample is 1.5% (same as population). Churn prevalence is 6% (same).
- **Full-dataset queries require re-running locally** — a user with a 16 GB laptop can load the full 4M-row Parquet into pandas for any query. The sample is a performance optimisation, not a correctness compromise.
