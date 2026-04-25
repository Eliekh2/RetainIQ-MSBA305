# Decision: Mongo → Postgres ETL to denormalised dimension table (not application-level JOINs)

## Decision
Customer profile data is pulled from MongoDB into a denormalised `dim_unified_wallet` table in Postgres via a scheduled ETL step (`src/integration/build_unified_view.py`). All analytical queries JOIN to this Postgres table — they do not call MongoDB directly.

## Alternatives considered
1. **Application-level JOIN (query Mongo + Postgres separately, merge in Python at query time)**
2. **MongoDB `$lookup` to pull transaction data into Mongo**
3. **Maintain profiles in Postgres JSONB alongside transactions**

## Why rejected
1. **Application-level JOIN:** Each query would require two round-trips (Postgres + Mongo) plus an in-memory merge. For the 5 analytical queries in §4.5 this is workable, but the pattern doesn't scale and makes `EXPLAIN ANALYZE` performance notes meaningless (two separate query planners). It also prevents SQL window functions and CTEs from spanning the join.
2. **MongoDB `$lookup` from transactions:** The transaction fact table has 500K rows — pulling that into Mongo for a `$lookup` would require replicating the fact table into MongoDB, defeating the purpose of having Postgres for structured relational data.
3. **Profiles in Postgres JSONB:** Defeats the polyglot persistence architecture story. If everything ends up in Postgres, there's no justification for MongoDB in §4.2.

## Trade-offs accepted
- **ETL lag:** The unified view is a snapshot, not live. If profiles are updated in Mongo, the ETL must re-run to reflect changes. At academic scale with static data this is not a concern.
- **Storage duplication:** Profile data exists in both Mongo (source of truth) and Postgres (derived dimension). The Mongo collection remains the authoritative copy; the Postgres dimension is a materialised projection.
