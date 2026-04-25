# Decision: Batch ingestion (not streaming)

## Decision
All three sources are ingested as scheduled batch loads, not streaming.

## Alternatives considered
1. **Apache Kafka streaming pipeline**
2. **Hybrid (batch + CDC for deltas)**

## Why rejected
1. **Kafka streaming:** Our analytical workload (churn patterns, monthly volume trends, fraud pattern discovery) operates on daily-or-longer windows. A customer's churn risk doesn't change minute-by-minute. Kafka adds broker infrastructure, consumer-group management, and exactly-once semantics — all overhead with zero analytical benefit at this scale.
2. **Hybrid (batch + CDC):** CDC is justified when source systems are high-velocity and downstream SLAs are tight. Our sources are all academic exports (Parquet from Hugging Face, team-generated JSON, one-time XML export) with no live CDC stream available. Implementing CDC on static files would be fiction.

## Trade-offs accepted
- **Up to 24-hour data latency** — interventions triggered by this pipeline (e.g., retention outreach for at-risk customers) happen on a next-business-day cadence, so latency is aligned with downstream action timescales.
- **No real-time fraud detection** — if fraud detection required sub-minute response, we would layer a streaming pipeline (Kafka Streams or Flink) in parallel. Noted as a future-work item in the architecture report.

## Scale path
- <500K rows: pandas + batch (current state)
- 500K–50M rows: PySpark on Databricks, batch
- >50M rows with real-time requirements: Kafka + Spark Streaming hybrid
