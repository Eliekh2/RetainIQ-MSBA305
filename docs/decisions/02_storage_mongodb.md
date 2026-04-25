# Decision: MongoDB Atlas for customer profile documents

## Decision
Use MongoDB Atlas M0 free tier as the document store for customer_profiles data (nested-capable JSON, 375,837 documents, schema-flexible).

## Alternatives considered
1. **PostgreSQL JSONB columns**
2. **Couchbase Capella**
3. **Flat JSON file only**

## Why rejected
1. **PostgreSQL JSONB:** The customer profile JSON has ~14 optional fields and evolves as KYC regulations change. A JSONB column on Postgres would work but loses native document-query idioms (dot-notation path queries, `$elemMatch`). Mixing our tabular fact tables with schema-flexible documents in one engine also weakens the "polyglot persistence" architectural narrative that justifies our design decisions.
2. **Couchbase Capella:** Requires a credit card and expires in 30 days. We need a solution the professor can run indefinitely after submission.
3. **Flat JSON file only:** No concurrent access, no query engine, no indexing. Analysts would have to load the entire 183 MB file into memory for every query. Rubric §4.5 requires query performance optimisation notes, which file-based storage cannot satisfy.

## Trade-offs accepted
- **No native JOINs with Postgres data** — mitigated by the integration layer (`src/integration/build_unified_view.py`), which exports a denormalised wallet-level dimension from Mongo to Postgres for cross-source queries.
- **512 MB Atlas free tier cap** — our JSON at 183 MB with indexes fits within ~350 MB, leaving headroom.
- **Eventual consistency on replica reads** — not a concern at academic scale with a single-region free-tier cluster.
