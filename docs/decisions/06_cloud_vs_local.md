# Decision: Cloud-hosted storage (Neon + Atlas) for the analytical tier

## Decision
Both databases are cloud-hosted (Neon for Postgres, Atlas for MongoDB). Raw data files are stored in Google Drive for team and professor access. Processed intermediate artifacts are kept local.

## Alternatives considered
1. **Local Postgres + local MongoDB (on each developer's machine)**
2. **AWS full stack (S3 + RDS + DocumentDB)**
3. **Self-hosted on a team member's home server**

## Why rejected
1. **Local only:** The professor cannot run queries against a local DB without installing Postgres and MongoDB on his machine or receiving a SQL dump. Cloud-hosted means he runs `pip install -r requirements.txt`, plugs in our `.env` credentials, and every query works immediately.
2. **AWS full stack:** AWS free tier requires credit card verification, has complex IAM setup for cross-service access, and expires after 12 months. Neon + Atlas are permanently-free tiers designed for exactly this prototyping use case.
3. **Self-hosted:** Single point of failure (whoever's laptop/server), no SLA, firewall issues for external access, port-forwarding complexity on residential ISPs.

## Trade-offs accepted
- **Vendor lock-in** — minimal. Both services expose standard PG wire protocol and MongoDB wire protocol; migration to RDS/DocumentDB or self-hosted is a connection-string change.
- **Internet dependency** — queries require internet access. Acceptable for an academic demo.
- **Cold-start latency on Neon scale-to-zero** — ~300 ms on first query after idle (see `01_storage_postgres.md`).
