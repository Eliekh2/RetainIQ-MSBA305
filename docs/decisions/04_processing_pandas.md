# Decision: pandas/Python local processing

## Decision
Use pandas + Python for all data cleaning, transformation, aggregation, and EDA. No Spark, no Dask, no distributed processing.

## Alternatives considered
1. **Apache Spark (PySpark)**
2. **Polars**

## Why rejected
1. **PySpark:** Our total working set (500K sampled rows + 375K profile docs + 28K XML events ≈ 900K rows) fits comfortably in memory on any modern laptop. Spark's JVM startup overhead alone (~30–60s) exceeds the total pandas processing time for our workload. Spark becomes cost-effective above ~10 GB or when distributed cluster resources exist; we have neither.
2. **Polars:** Polars is genuinely faster than pandas for our workload size, but every team member's existing notebooks are pandas-based. Switching would require rewriting working code with zero grading benefit — the rubric does not reward faster execution, it rewards correct methodology.

## Trade-offs accepted
- **Single-node memory ceiling** — at 10× data volume we would migrate transformation to Spark. The ingestion and loading scripts are designed to be refactor-friendly (functional style, no global state).
- **No lazy evaluation** — all intermediate DataFrames materialise in memory. Mitigated by explicit cleanup after heavy transformations.
