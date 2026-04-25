"""
Runs all 5 analytical queries and returns results as DataFrames.
Also runs the MongoDB Q3 aggregation via pymongo.
"""
from pathlib import Path
import time
import pandas as pd
from sqlalchemy import text
from src.config import get_pg_engine, get_mongo_db
from src.logging_setup import get_logger

logger = get_logger(__name__)

SQL_DIR = Path("sql/queries")


def _run_sql(query: str, label: str) -> tuple[pd.DataFrame, float]:
    """Execute a SQL query; return (DataFrame, elapsed_seconds)."""
    engine = get_pg_engine()
    t0 = time.perf_counter()
    with engine.connect() as conn:
        df = pd.read_sql(text(query), conn)
    elapsed = time.perf_counter() - t0
    logger.info(f"{label}: {len(df)} rows in {elapsed:.2f}s")
    return df, elapsed


def q1_monthly_volume() -> tuple[pd.DataFrame, float]:
    sql = (SQL_DIR / "q1_monthly_volume.sql").read_text()
    return _run_sql(sql, "Q1 monthly_volume")


def q2_churn_by_kyc_channel() -> tuple[pd.DataFrame, float]:
    sql = (SQL_DIR / "q2_churn_by_kyc_channel.sql").read_text()
    return _run_sql(sql, "Q2 churn_by_kyc_channel")


def q3_mongo_profile_distribution() -> tuple[list, float]:
    """MongoDB aggregation: profiles by account_status × preferred_language."""
    db  = get_mongo_db()
    col = db["customer_profiles"]
    pipeline = [
        {"$group": {
            "_id": {
                "account_status":     "$account_status",
                "preferred_language": "$preferred_language",
            },
            "count":   {"$sum": 1},
            "avg_age": {"$avg": "$age"},
        }},
        {"$sort": {"count": -1}},
    ]
    t0 = time.perf_counter()
    results = list(col.aggregate(pipeline))
    elapsed = time.perf_counter() - t0
    logger.info(f"Q3 mongo_profile_distribution: {len(results)} groups in {elapsed:.2f}s")
    return results, elapsed


def q4_top_wallets_join() -> tuple[pd.DataFrame, float]:
    sql = (SQL_DIR / "q4_top_wallets_join.sql").read_text()
    return _run_sql(sql, "Q4 top_wallets_join")


def q5_wallet_mom_growth() -> tuple[pd.DataFrame, float]:
    sql = (SQL_DIR / "q5_wallet_mom_growth.sql").read_text()
    return _run_sql(sql, "Q5 wallet_mom_growth")


def run_all() -> dict:
    """Run all 5 queries and return dict of {name: (result, elapsed)}."""
    return {
        "q1_monthly_volume":          q1_monthly_volume(),
        "q2_churn_by_kyc_channel":    q2_churn_by_kyc_channel(),
        "q3_mongo_profile_dist":      q3_mongo_profile_distribution(),
        "q4_top_wallets_join":        q4_top_wallets_join(),
        "q5_wallet_mom_growth":       q5_wallet_mom_growth(),
    }
