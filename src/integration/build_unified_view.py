"""
Builds dim_unified_wallet by joining MongoDB customer profiles
with wallet-level aggregates from Postgres.

Pattern: Mongo → Python → Postgres ETL (denormalized integration table).
This avoids application-level JOINs at query time and exposes a single
unified dimension for all analytical queries.
"""
import pandas as pd
from sqlalchemy import text
from src.config import get_pg_engine, get_mongo_db
from src.logging_setup import get_logger

logger = get_logger(__name__)

COLLECTION = "customer_profiles"
BATCH_SIZE = 10_000


def _pull_mongo_profiles() -> pd.DataFrame:
    """Pull all customer profiles from MongoDB into a DataFrame."""
    db  = get_mongo_db()
    col = db[COLLECTION]
    logger.info(f"Pulling {col.count_documents({}):,} profiles from MongoDB...")
    docs = list(col.find({}, {"_id": 1, "full_name": 1, "age": 1, "gender": 1,
                               "state": 1, "city": 1, "registration_date": 1,
                               "account_status": 1, "referral_source": 1,
                               "preferred_language": 1, "linked_bank": 1,
                               "support_tier": 1}))
    df = pd.DataFrame(docs)
    df.rename(columns={"_id": "wallet_id"}, inplace=True)
    df["registration_date"] = pd.to_datetime(df["registration_date"], errors="coerce").dt.date
    logger.info(f"Pulled {len(df):,} profile documents")
    return df


def _pull_pg_agg() -> pd.DataFrame:
    """Pull wallet aggregations from Postgres."""
    engine = get_pg_engine()
    query = """
        WITH kyc AS (
            SELECT wallet_id,
                   MODE() WITHIN GROUP (ORDER BY kyc_tier) AS kyc_tier
            FROM fact_mobile_money_tx
            GROUP BY wallet_id
        )
        SELECT
            m.wallet_id,
            m.total_tx_count,
            m.total_volume_ngn,
            m.total_fees_ngn,
            m.avg_tx_amount,
            m.first_tx_date,
            m.last_tx_date,
            m.dominant_channel,
            m.dominant_tx_type,
            m.fraud_flag,
            m.churn_30d,
            k.kyc_tier,
            CASE WHEN x.wallet_id IS NOT NULL THEN TRUE ELSE FALSE END AS has_xml_activity
        FROM dim_wallet_agg_mm m
        LEFT JOIN kyc k USING (wallet_id)
        LEFT JOIN dim_wallet_agg_xml x USING (wallet_id)
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    logger.info(f"Pulled {len(df):,} wallet aggregations from Postgres")
    return df


def run(force_rebuild: bool = False) -> None:
    """Build dim_unified_wallet. Skips if already populated unless force_rebuild=True."""
    engine = get_pg_engine()
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM dim_unified_wallet")).scalar()
    if existing > 0 and not force_rebuild:
        logger.info(f"dim_unified_wallet already has {existing:,} rows — skipping")
        return

    profiles = _pull_mongo_profiles()
    pg_agg   = _pull_pg_agg()

    # Join: profiles (left) JOIN pg_agg (right)
    # Only wallets with a profile get into the unified view
    unified = profiles.merge(pg_agg, on="wallet_id", how="left")
    unified["has_xml_activity"] = unified["has_xml_activity"].fillna(False)
    unified.rename(columns={"referral_source": "acquisition_channel"}, inplace=True)

    logger.info(f"Unified view: {len(unified):,} wallets "
                f"({unified['total_tx_count'].notna().sum():,} with transaction data)")

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dim_unified_wallet CASCADE"))

    unified.to_sql(
        "dim_unified_wallet",
        engine,
        if_exists="append",
        index=False,
        chunksize=BATCH_SIZE,
        method="multi",
    )

    with engine.connect() as conn:
        final = conn.execute(text("SELECT COUNT(*) FROM dim_unified_wallet")).scalar()
    logger.info(f"dim_unified_wallet final count: {final:,}")
    assert final > 0, "dim_unified_wallet is empty after build"


if __name__ == "__main__":
    run()
