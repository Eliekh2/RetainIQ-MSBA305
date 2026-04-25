# AI Usage Log — RetainIQ Pipeline (MSBA 305)

Throughout this project, our team used Claude (Anthropic) as a learning aid and technical reference. We treated AI the way we would treat office hours with a teaching assistant — asking for explanations of unfamiliar concepts, comparing trade-offs between approaches, reviewing our code for correctness and style, and debugging errors together. We did not use AI to generate code we did not understand or to make architectural decisions on our behalf. Every prompt below reflects a moment where a team member was stuck, unsure, or wanted to validate their own reasoning before proceeding.

Every architectural decision, every line of code, and every analytical interpretation in this submission was made and understood by team members, not delegated. Where AI explained a concept or outlined options, we evaluated those explanations against our specific data, our storage constraints, and our project requirements before acting. The log below documents this process in the format required by the rubric: the prompt we asked, what the AI explained, what we then did with that explanation, how we adapted it to our context, and what we learned.

---

## AI Interaction 1

**Date:** March 2026
**Phase:** Ingestion
**Task Context:** We were about to write the Parquet ingestion module and needed to decide whether to use `pandas.read_parquet()` directly or use the PyArrow Dataset API. The file is 237 MB and we were unsure whether the lower-level API would give us meaningful performance advantages worth the added complexity.

**Prompt:** "Can you explain the difference between using `pandas.read_parquet()` and the PyArrow Dataset API directly for reading a single large Parquet file? We have a 237 MB file and I want to understand whether the lower-level API gives us a meaningful performance advantage before I decide which to use."

**AI Response Summary:** Claude explained that `pandas.read_parquet()` is a thin convenience wrapper around the PyArrow engine — for a single flat file read into a DataFrame, the two are functionally identical in performance. The PyArrow Dataset API adds value in specific scenarios: predicate pushdown (filtering rows before materialization), selective column projection on partitioned datasets, and streaming reads on files too large for memory. None of those scenarios apply to a single flat file loaded entirely into memory. The distinction matters primarily for multi-file partitioned datasets stored in a directory structure.

**How We Used It:** We confirmed `pandas.read_parquet()` was the right choice for our use case and wrote `ingest_parquet.py` using it. We did not add a PyArrow dependency to the module.

**Modifications & Decisions:** We added a `columns=` parameter in the ingestion function for EDA runs to avoid loading all columns during exploratory work, which we decided on ourselves after seeing the schema — the AI did not suggest this.

**What We Learned:** `pandas.read_parquet()` is not a simplified fallback — it is the same PyArrow engine with a more convenient interface. The performance gap only emerges with partitioned datasets or selective column reads on very large multi-file collections.

---

## AI Interaction 2

**Date:** March 2026
**Phase:** Ingestion
**Task Context:** Before writing the XML parser for the Bilpay settlement feed, a team member was trying to extract the `net_amount` field using Python's `xml.etree.ElementTree` and kept getting `None`. The amount field lives at `financials/amount/net_amount` — three levels deep — and the initial `.find('net_amount')` call was not working.

**Prompt:** "Can you walk me through how nested element lookup works in Python's ElementTree? In our XML file, the net_amount is at financials/amount/net_amount but when I call `.find('net_amount')` on the transaction element I get None. What am I misunderstanding about how find() works?"

**AI Response Summary:** Claude explained that `ElementTree.find()` only searches the direct children of the element it is called on — it does not recurse into descendants unless you use an XPath expression. Calling `.find('net_amount')` on a `<transaction>` element will return `None` if `<net_amount>` is three levels down, because the direct children of `<transaction>` are `<identifiers>`, `<customer>`, `<financials>`, etc. The correct approach is either a full XPath path `.find('financials/amount/net_amount')` or `.findtext()` which returns the text content directly with a default fallback. Claude also noted that XML stores all values as strings — there is no native numeric type — so the extracted value needs explicit type conversion after parsing.

**How We Used It:** After understanding this, the team member rewrote `_parse_tx()` in `ingest_xml.py` using explicit XPath paths for every financial field, and added `int()` casts (later changed to `pd.array(..., dtype='Int64')` in the cleaning step).

**Modifications & Decisions:** We chose explicit XPath paths over recursive search (`.findall('.//')`) because our schema was fixed. Recursive search would silently return the wrong field if Bilpay ever renamed a nested tag — explicit paths fail loudly, which is safer.

**What We Learned:** `ElementTree.find()` searches direct children only — XPath path expressions are required for any nested lookup. This is a common source of silent `None` values in XML parsing.

---

## AI Interaction 3

**Date:** March 2026
**Phase:** Storage
**Task Context:** Before finalising the schema design, we were debating where to store the 375,837 customer profile documents. The records are mostly flat but have a few optional nested fields. We were considering either adding them to Postgres with JSONB columns or using MongoDB Atlas.

**Prompt:** "I'm deciding between storing customer profiles in PostgreSQL with JSONB columns versus MongoDB. Our dataset has about 375K records with mostly flat fields but some optional nested structures. Can you compare the trade-offs for this specific use case so I can make an informed choice?"

**AI Response Summary:** Claude explained that JSONB in Postgres works well when you need to query nested fields inside SQL JOIN expressions alongside relational data — but every query against nested fields requires explicit casting and the syntax is verbose compared to native document queries. MongoDB's document model is more natural when the document is the primary unit of retrieval and you are running aggregation pipelines over document-level fields (like demographic group-bys). For a dataset where profiles are mostly flat but retrieval is document-centric (full profile fetch) rather than column-centric (cross-join to transaction facts), MongoDB is more idiomatic. JSONB adds complexity without benefit when the nested fields are optional and rarely queried in SQL.

**How We Used It:** We chose MongoDB Atlas M0 for customer profiles. The deciding factor was that Q3's demographic analysis is a document-level aggregation pipeline — summing counts and averaging ages by group — which is natural in MQL and awkward in SQL over JSONB.

**Modifications & Decisions:** We still ETL'd the profiles into `dim_unified_wallet` in Postgres via `build_unified_view.py` because Q4 and Q5 needed wallet profiles alongside transaction facts in a single SQL query. We did not do application-level joins — the AI mentioned that option but we rejected it as too slow at 375K rows.

**What We Learned:** JSONB is the right choice when nested data participates in SQL joins; MongoDB is the right choice when the document is the primary retrieval unit and aggregations are document-centric rather than relational.

---

## AI Interaction 4

**Date:** March 2026
**Phase:** Storage
**Task Context:** After designing the schema, we discovered that loading all 4 million Parquet rows into Neon's free tier would exceed its 0.5 GB storage cap. We needed to reduce the row count and were debating between simple random sampling and a different approach.

**Prompt:** "Can you explain the difference between stratified sampling and simple random sampling, and when each is appropriate for financial transaction data? We have 4M rows and need to reduce to roughly 500K to fit our cloud database's storage limit."

**AI Response Summary:** Claude explained that simple random sampling works correctly when all rows are equally representative of the population, but fails when the population contains rare subgroups that need to be preserved proportionally. For transaction data with rare classes like `fraud_flag` (which might appear in only 1–2% of rows), a random 12.5% sample might include very few fraud cases purely by chance, biasing any downstream fraud analysis. Stratified sampling divides the population into strata — combinations of important categorical columns — and samples a fixed fraction from each stratum, guaranteeing that rare subgroups appear at their natural population rate in the sample.

**How We Used It:** We implemented stratified sampling in `clean_parquet.py` stratified on `(transaction_type, churn_30d, fraud_flag)` using `groupby().apply(lambda g: g.sample(frac=0.125, random_state=42))`, after deciding ourselves which columns were the most analytically critical strata.

**Modifications & Decisions:** We verified post-sampling that `fraud_flag` and `churn_30d` proportions matched the original dataset within 0.5 percentage points. We also set `random_state=42` for reproducibility so any team member re-running the pipeline gets the same sample.

**What We Learned:** Stratified sampling is the correct approach whenever downstream analysis depends on the distribution of minority classes — simple random sampling of imbalanced data silently underrepresents rare but analytically important categories.

---

## AI Interaction 5

**Date:** March 2026
**Phase:** Storage / Architecture
**Task Context:** Early in the project, before choosing any specific database, we needed to identify cloud-hosted options for both a relational database and a document database that would allow the professor and all team members to connect without any local database installation — just a Python package and a connection string.

**Prompt:** "We need a cloud-hosted PostgreSQL instance and a cloud-hosted MongoDB instance that are both free, require no local installation to connect to, and can be shared with a professor who needs to run our notebooks without any database setup beyond installing Python packages. What are our main options and what are their practical limits?"

**AI Response Summary:** Claude outlined the main free-tier options: for Postgres — Neon (0.5 GB storage, serverless, standard `postgresql://` connection string, no IP restriction on free tier), Supabase (500 MB, similar), and Railway (smaller free tier with usage limits). For MongoDB — Atlas M0 (512 MB, free forever, accessible via a `mongodb+srv://` URI). Claude highlighted that Neon and Atlas M0 are the most widely used combination for academic data pipelines because both have no IP whitelist requirements on free tiers (critical for a professor connecting from any network), both support standard library connection strings with no special SDK, and both have enough free storage for classroom-scale datasets.

**How We Used It:** We chose Neon Postgres and MongoDB Atlas M0. After setting up both, we hardcoded the connection strings as fallback defaults in `src/config.py` using `os.getenv("KEY", "hardcoded_default")` so that the professor needs no `.env` file — the notebooks connect automatically.

**Modifications & Decisions:** We chose Neon over Supabase because Neon's serverless architecture handles the connect-disconnect pattern of Jupyter notebooks more gracefully — Supabase keeps a persistent connection pool that can exhaust on a free tier if notebooks are left open. We reached this conclusion from reading Neon's documentation ourselves after the AI gave us the initial shortlist.

**What We Learned:** Free-tier cloud databases differ not just in storage limits but in connection model — Neon's serverless (on-demand compute) is better suited to notebook workloads than always-on free tiers that have connection count limits.

---

## AI Interaction 6

**Date:** March 2026
**Phase:** Cleaning
**Task Context:** While writing the Parquet cleaning script, we were debating what to do with high-value transaction outliers. Some transactions have amounts more than 10× the median. We wanted to understand the right approach before implementing anything.

**Prompt:** "I'm trying to understand why a cleaning script should flag outliers instead of removing them in financial transaction data. Some of our transactions have amounts more than 10 times the median. Can you walk me through the trade-offs between removing versus flagging, specifically for a financial dataset?"

**AI Response Summary:** Claude explained that in financial data, high-value transactions are often the most analytically significant records — large deposits, wholesale transfers, and cross-border remittances are genuine events, not measurement errors. Removing them would bias aggregate metrics like average transaction value significantly downward and would destroy the information that high-value customers exist. IQR-based flagging adds a boolean column marking values outside `[Q1 − 1.5·IQR, Q3 + 1.5·IQR]` without modifying the original values, giving downstream analysts the choice to include or exclude outliers depending on their specific question. Removal is appropriate only when outliers represent instrument error or data entry mistakes — identifiable by being physically impossible (e.g., a negative balance after a deposit).

**How We Used It:** We implemented IQR flags as three separate boolean columns — `is_amount_ngn_outlier`, `is_fee_ngn_outlier`, and `is_balance_after_ngn_outlier` — in `clean_parquet.py`. The original amount columns were left completely untouched.

**Modifications & Decisions:** We added three separate flags rather than a single combined outlier flag because each financial column has its own IQR threshold and a downstream analyst might legitimately want to filter fee outliers without removing high-value transactions. This was our own design decision.

**What We Learned:** IQR-based flagging is the correct pattern for financial outliers because it preserves regulatory completeness (financial records must remain auditable) while surfacing anomalies for downstream consumers to handle contextually.

---

## AI Interaction 7

**Date:** March 2026
**Phase:** Cleaning
**Task Context:** After parsing the XML source, we found that 13,937 rows had duplicate `receipt_number` values — all of them were `TOP_UP` transactions. We were unsure whether this indicated corrupted data that should be dropped, or whether it had another explanation.

**Prompt:** "I found that 13,937 rows in our XML source all share duplicate receipt_number values, and all of them are TOP_UP transactions. Is this likely to be a data quality problem that disqualifies the rows, or is there a known pattern that explains this? How should I decide what to do?"

**AI Response Summary:** Claude explained that batch-generated placeholder UUIDs are a documented pattern in settlement systems where a reconciliation export generates a single identifier for an entire transaction batch rather than a unique ID per transaction. The key diagnostic is whether the rows are true duplicates (same `wallet_id`, same `amount`, same `timestamp` — indicating the same event was recorded twice) or identifier-sharing non-duplicates (same `receipt_number`, but different `wallet_id`, `amount`, and `timestamp` on every row — indicating the ID was fabricated). If the rows are non-duplicates, the correct fix is to regenerate the identifiers, not to drop the rows. Claude also distinguished between `receipt_number` (an internal transaction identifier) and `reference_number` (used for external reconciliation), noting that these should be handled differently.

**How We Used It:** We confirmed that all 13,937 TOP_UP rows had distinct `wallet_id`, `amount`, and `timestamp` values — genuine non-duplicate transactions. We then implemented UUID regeneration using `uuid.uuid4()` in `clean_xml.py` for the `receipt_number` column, and added an `is_ref_dup` boolean flag on `reference_number` without modifying it.

**Modifications & Decisions:** We chose to regenerate `receipt_number` but only flag `reference_number` because modifying reference numbers could break external reconciliation if this were a production feed. We made that distinction ourselves — the AI's explanation clarified the difference but did not tell us which to fix.

**What We Learned:** Duplicate identifiers require root cause diagnosis before action — batch placeholder UUIDs need regeneration while true record duplicates need deduplication; conflating the two leads to either data loss or silent identifier collisions.

---

## AI Interaction 8

**Date:** March 2026
**Phase:** Cleaning
**Task Context:** After implementing SHA-256 hashing of phone numbers in `clean_xml.py`, a team member wanted to validate that the no-salt design decision was correct before finalising the implementation. The hash is used for cross-source linkage, which requires determinism.

**Prompt:** "We're hashing phone numbers with SHA-256 with no salt. My reasoning is that we need deterministic linkage — the same phone number must always hash to the same value so we can correlate records across sources. I think the no-salt approach is fine for our academic pipeline, but I want to check whether I'm missing a security risk we should be documenting."

**AI Response Summary:** Claude confirmed that the reasoning was correct for the stated use case: deterministic hashing without a salt is appropriate when the hash is used as a pseudonymous cross-source key rather than for authentication or password storage. The security risk that the no-salt design does not mitigate is a precomputed rainbow table attack — because phone numbers occupy a finite, predictable space (country code plus a fixed-length digit string), a lookup table of all possible phone numbers and their SHA-256 hashes could reverse most hashes. For a production system handling real customer data, HMAC-SHA256 with a server-side secret is the correct approach because it makes precomputation infeasible. For an academic pipeline with synthetic data where cross-source linkage is the primary requirement, the no-salt design is defensible provided the limitation is explicitly documented.

**How We Used It:** We kept the SHA-256 no-salt implementation and documented the production limitation — including the HMAC-SHA256 alternative — in `docs/appraisals/xml_appraisal.md` §5 so the professor sees that the team understood the trade-off, not that we overlooked it.

**Modifications & Decisions:** We added explicit language to the documentation stating "a production system would use HMAC-SHA256 with a server-side secret" rather than just "this is a known limitation" — that phrasing shows awareness of the specific fix, not just the existence of a gap.

**What We Learned:** Deterministic hashing is the correct choice for pseudonymous identifiers that need cross-source linkage; the trade-off is vulnerability to rainbow table attacks on predictable input spaces, which must be documented and addressed in any production deployment.

---

## AI Interaction 9

**Date:** April 2026
**Phase:** Processing
**Task Context:** While building `dim_unified_wallet` in `build_unified_view.py`, we needed to derive a single dominant channel and dominant transaction type per wallet from thousands of individual transaction rows. We had seen `MODE() WITHIN GROUP` referenced in PostgreSQL documentation but did not fully understand it.

**Prompt:** "What does `MODE() WITHIN GROUP (ORDER BY ...)` do in PostgreSQL and why would I use it instead of a regular GROUP BY with COUNT and ORDER BY to find the most frequent value in a column?"

**AI Response Summary:** Claude explained that `MODE() WITHIN GROUP` is an ordered-set aggregate — a category of aggregate function that operates on a sorted sequence of values rather than a simple grouped set. It returns the value that appears most frequently within the group in a single expression, without a subquery. The alternative — GROUP BY the column, COUNT occurrences, ORDER BY count DESC, LIMIT 1 — requires a separate subquery or CTE for each column you want the mode of, making the SQL verbose when you need the mode of multiple columns simultaneously. In PostgreSQL, `MODE() WITHIN GROUP` can be used directly in a `SELECT` alongside `SUM()`, `AVG()`, and other standard aggregates in one pass over the data.

**How We Used It:** We used `MODE() WITHIN GROUP (ORDER BY channel)` and `MODE() WITHIN GROUP (ORDER BY transaction_type)` in the `dim_unified_wallet` build query, replacing what would have been two separate CTEs.

**Modifications & Decisions:** We verified that PostgreSQL's `MODE()` handles ties by returning one of the tied values non-deterministically (the documentation does not guarantee which tied value is chosen). We confirmed this was acceptable for a "dominant channel" use case where exact tie-breaking is not analytically meaningful.

**What We Learned:** Ordered-set aggregates like `MODE()` are a distinct category from regular aggregates — they operate on a sorted sequence and collapse it to a single derived value, which is conceptually different from `COUNT(*)` or `SUM()` operating on a multiset.

---

## AI Interaction 10

**Date:** April 2026
**Phase:** Querying
**Task Context:** Writing Q2 (churn rate by KYC tier and channel), we needed to compute a percentage where some groups might have zero wallets. We had seen `NULLIF` used in division expressions in examples but did not fully understand what it does or why it is the idiomatic choice.

**Prompt:** "Can you explain what `NULLIF` does in SQL and why it's used specifically in division expressions for percentage calculations? I want to calculate churn_rate = churned_wallets / total_wallets * 100 but some groups might have zero total wallets."

**AI Response Summary:** Claude explained that `NULLIF(x, y)` returns `NULL` if `x` equals `y`, otherwise returns `x` unchanged. In a division expression, wrapping the denominator in `NULLIF(denominator, 0)` converts a zero denominator to `NULL`, which causes the entire division to return `NULL` rather than a division-by-zero runtime error. This is more concise than `CASE WHEN denominator = 0 THEN NULL ELSE numerator / denominator END` and composes cleanly inside `ROUND()`. `NULL` results propagate correctly through subsequent aggregations — `AVG()` over a column containing `NULL` values automatically excludes them, which is the desired behaviour for "groups with no members have no churn rate."

**How We Used It:** We implemented `ROUND(SUM(churned)::NUMERIC / NULLIF(COUNT(DISTINCT wallet_id), 0) * 100, 2)` in Q2.

**Modifications & Decisions:** We added the `::NUMERIC` cast before the division ourselves after noticing during testing that integer division in PostgreSQL truncates — `3 / 4` returns `0`, not `0.75`. The AI's initial explanation assumed float inputs and did not mention this. We caught the truncation issue by checking a result that should have been 33.3% and got 0%.

**What We Learned:** `NULLIF` is the idiomatic PostgreSQL pattern for safe division; it must be combined with an explicit `::NUMERIC` cast when the numerator and denominator are integers, because PostgreSQL performs integer division by default.

---

## AI Interaction 11

**Date:** April 2026
**Phase:** Querying
**Task Context:** Running `build_unified_view.py` after a schema update failed with a column-not-found error even though the column was present in `schema.sql`. We were unsure why the schema file and the live database were out of sync.

**Prompt:** "My `build_unified_view.py` is failing with 'column total_fees_ngn of relation dim_unified_wallet does not exist'. The column is defined in my `schema.sql`. What does this error mean and what should I check first to understand why the table and the schema file are out of sync?"

**AI Response Summary:** Claude explained that `CREATE TABLE IF NOT EXISTS` is idempotent only on the table's existence, not its structure. If `dim_unified_wallet` was created during an earlier pipeline run using the previous schema definition, and the schema was later updated to add columns, the `IF NOT EXISTS` clause will silently skip the entire `CREATE TABLE` statement — including the new column definitions — because the table already exists. The fix is either `DROP TABLE dim_unified_wallet CASCADE` followed by re-running the schema script, or an `ALTER TABLE ... ADD COLUMN` migration. The choice depends on whether existing data in the table needs to be preserved.

**How We Used It:** We dropped and recreated `dim_unified_wallet` after confirming it is a fully derived table (rebuilt from MongoDB profiles + Postgres transaction aggregates with no source data of its own). We then audited `dim_wallet_agg_mm` and `dim_wallet_agg_xml` for the same issue.

**Modifications & Decisions:** We chose DROP + recreate over ALTER TABLE because the table has no source data — it is rebuilt deterministically every time `build_unified_view.py` runs. We also added a comment to `postgres_setup.py` warning that schema column additions require a table drop.

**What We Learned:** `CREATE TABLE IF NOT EXISTS` does not perform schema migrations — it only creates the table if it does not exist. Any structural change to an existing table requires an explicit `ALTER TABLE` or a DROP + recreate.

---

## AI Interaction 12

**Date:** April 2026
**Phase:** Visualization
**Task Context:** Designing the charts for notebook 07's visualization report, we were unsure whether to use a line chart or bar chart for the month-over-month volume trend, and how to best show the churn rate segmented by KYC tier and acquisition channel simultaneously.

**Prompt:** "Can you walk me through what chart types are most appropriate for two visualizations: one showing monthly transaction volume over time, and one showing churn rate broken down across two categorical dimensions — KYC tier and acquisition channel? I want to understand the reasoning, not just get a recommendation."

**AI Response Summary:** Claude explained that chart type selection is driven by the nature of the data and the comparison the reader needs to make. Time-series data (monthly volume) calls for a line chart because lines convey continuity — the reader's eye naturally reads trend and direction between months. Bar charts work for time series but imply discrete, unconnected periods. For two-dimensional categorical breakdowns (KYC tier × channel), a grouped bar chart (one cluster per KYC tier, individual bars per channel within each cluster) allows direct visual comparison both within a tier (across channels) and across tiers (same channel). A heatmap would work for the same data but requires more cognitive effort to read exact values.

**How We Used It:** We used a line chart with point markers for the MoM volume trend and a grouped bar chart for the churn segmentation in notebook 07.

**Modifications & Decisions:** We added a secondary y-axis to overlay transaction count (bars) against total volume (line) in a dual-axis combo chart for the MoM panel — this was our own addition after seeing the single-axis draft and deciding the transaction count context was important for interpreting volume changes.

**What We Learned:** Chart type choice is a communication decision, not a stylistic one — the geometry should match the cognitive task: line for trend, grouped bars for multi-dimensional categorical comparison, heatmap for dense matrix data.

---

## AI Interaction 13

**Date:** April 2026
**Phase:** Governance
**Task Context:** While writing the governance documentation and the XML source appraisal, we were debating whether the IDR/NGN currency mismatch should be framed as a known limitation or treated as a correctness bug requiring a fix before submission.

**Prompt:** "Our XML source contains amounts in Indonesian Rupiah (IDR) while our Parquet source contains amounts in Nigerian Naira (NGN). We considered this a known limitation rather than implementing a currency conversion layer. Is that framing defensible for an academic submission, and what should the documentation say to make it credible rather than just an excuse?"

**AI Response Summary:** Claude explained that a known limitation is academically defensible under three conditions: (a) it is explicitly documented with a clear statement of its scope impact, not just its existence; (b) the current pipeline design does not silently produce incorrect cross-currency comparisons — if IDR and NGN amounts never appear in the same aggregation expression, the limitation is contained rather than corrupting; (c) the documentation describes what a production implementation would look like. The framing "we did not implement X" is weak; the framing "we audited the pipeline and confirmed X's absence does not affect any current query output, and production would address it by Y" is strong.

**How We Used It:** We audited `dim_unified_wallet` and confirmed that IDR amounts from `fact_xml_transactions` never flow into `total_volume_ngn` — only a `has_xml_activity` boolean is stored. We then confirmed that none of Q1–Q5 compare IDR and NGN amounts in the same expression. With that evidence, we kept the known limitation framing and added specific language to `docs/governance.md` §6 and `docs/appraisals/xml_appraisal.md` §5 stating which tables contain IDR, which queries are unaffected, and what a production FX rate layer would involve.

**Modifications & Decisions:** We added the specific sentence "no current Q1–Q5 query compares IDR and NGN amounts in the same expression" to the documentation — the AI's explanation made clear that a vague limitation statement is weaker than one with a specific scope boundary backed by evidence.

**What We Learned:** A documented limitation is credible only when the team has actively audited its blast radius and can state precisely what is and is not affected — "we know about it and it does not affect our current outputs" is a different claim than "we noticed it but did not investigate."

---

## AI Interaction 14

**Date:** March 2026
**Phase:** Cleaning (cross-cutting)
**Task Context:** Running the cleaning pipeline on a Windows machine, the script crashed with a `UnicodeEncodeError` on a logger line that contained an arrow character (`→`). The error appeared in `clean_parquet.py` first but would affect all three cleaning modules.

**Prompt:** "I'm getting `UnicodeEncodeError: 'charmap' codec can't encode character '→'` when running my cleaning script on Windows. The error is happening at a `logger.info()` call. What's causing this and what's the most portable fix?"

**AI Response Summary:** Claude explained that Windows console output defaults to the system's ANSI code page — most commonly `cp1252` in Western locales — which is a subset of Latin-1 and cannot encode Unicode characters outside that range. The right arrow `→` (U+2192) is outside cp1252. Three fixes exist: setting `PYTHONIOENCODING=utf-8` as an environment variable, configuring the stream handler with `encoding='utf-8'`, or replacing the Unicode character with an ASCII equivalent. The environment variable fix is fragile because it must be set by every person running the code. The stream handler fix requires modifying the logging configuration. The ASCII replacement is the most portable because it requires no environment configuration and works on any platform.

**How We Used It:** We replaced all `→` characters in `logger.info()` and `logger.warning()` calls across `clean_parquet.py`, `clean_json.py`, and `clean_xml.py` with `->`.

**Modifications & Decisions:** We explicitly rejected the `PYTHONIOENCODING` environment variable fix because it is invisible — a professor running on a fresh Windows install would hit the exact same error with no explanation. The ASCII replacement is a one-time code change with no environment dependency and no documentation burden. We also decided to fix all three cleaning modules at once rather than waiting to see if the error appeared in the others.

**What We Learned:** Windows `cp1252` is not Unicode — it covers only the Latin-1 supplement range, and any Python string containing characters outside that range will raise `UnicodeEncodeError` when written to an unconfigured Windows console. The portable principle is: log output should always be ASCII-safe unless the encoding is explicitly controlled end-to-end.
