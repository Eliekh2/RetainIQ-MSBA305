"""
Loads a stratified 500K-row sample of the parquet source into Postgres.

Stratification keys: (transaction_type, churn_30d, fraud_flag)
This preserves the distribution of rare events (1.5% fraud, 6% churn).
random_state=42 for reproducibility.

Also builds dim_wallet_agg_mm from the sample.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import text
from src.config import get_pg_engine
from src.ingestion import ingest_parquet
from src.cleaning import clean_parquet
from src.logging_setup import get_logger

logger = get_logger(__name__)

SAMPLE_SIZE     = 500_000
RANDOM_STATE    = 42
SAMPLE_PATH     = Path("data/processed/parquet_sample_500k.parquet")
CLEANED_PATH    = Path("data/processed/parquet_cleaned.parquet")
AUDIT_PATH      = Path("data/audit/parquet_load_audit.json")
STRAT_KEYS      = ["transaction_type", "churn_30d", "fraud_flag"]
CHUNKSIZE       = 10_000


def build_sample(df: pd.DataFrame, n: int = SAMPLE_SIZE) -> pd.DataFrame:
    """Stratified sample of n rows from df on STRAT_KEYS."""
    total = len(df)
    frac  = min(n / total, 1.0)
    sample = (
        df.groupby(STRAT_KEYS, group_keys=False, observed=True)
          .apply(lambda g: g.sample(frac=frac, random_state=RANDOM_STATE))
    )
    # Top-up or trim to exactly n
    if len(sample) < n:
        remaining = df.drop(sample.index).sample(n - len(sample), random_state=RANDOM_STATE)
        sample = pd.concat([sample, remaining])
    elif len(sample) > n:
        sample = sample.sample(n, random_state=RANDOM_STATE)
    sample = sample.reset_index(drop=True)
    logger.info(f"Sample: {len(sample):,} rows (target {n:,})")
    return sample


def _build_wallet_agg(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate sample to wallet level for dim_wallet_agg_mm."""
    agg = df.groupby("wallet_id").agg(
        total_tx_count   =("transaction_id",       "count"),
        total_volume_ngn =("amount_ngn",           "sum"),
        total_fees_ngn   =("fee_ngn",              "sum"),
        avg_tx_amount    =("amount_ngn",           "mean"),
        first_tx_date    =("timestamp",            "min"),
        last_tx_date     =("timestamp",            "max"),
        fraud_flag       =("fraud_flag",           "any"),
        churn_30d        =("churn_30d",            "any"),
    ).reset_index()

    dom_channel = (
        df.groupby(["wallet_id", "channel"])["transaction_id"]
          .count().reset_index()
          .sort_values("transaction_id", ascending=False)
          .drop_duplicates("wallet_id")[["wallet_id", "channel"]]
          .rename(columns={"channel": "dominant_channel"})
    )
    dom_type = (
        df.groupby(["wallet_id", "transaction_type"])["transaction_id"]
          .count().reset_index()
          .sort_values("transaction_id", ascending=False)
          .drop_duplicates("wallet_id")[["wallet_id", "transaction_type"]]
          .rename(columns={"transaction_type": "dominant_tx_type"})
    )
    agg = agg.merge(dom_channel, on="wallet_id", how="left")
    agg = agg.merge(dom_type,    on="wallet_id", how="left")
    agg["first_tx_date"] = agg["first_tx_date"].dt.date
    agg["last_tx_date"]  = agg["last_tx_date"].dt.date
    return agg


def _validate_pre_load(df: pd.DataFrame) -> None:
    """Assertions that must pass before committing any rows."""
    dup_pk = df["transaction_id"].duplicated().sum()
    assert dup_pk == 0, f"PK violation: {dup_pk:,} duplicate transaction_ids"
    bad_wlt = (~df["wallet_id"].str.match(r'^WLT-\d{8}$')).sum()
    assert bad_wlt == 0, f"FK format: {bad_wlt:,} wallet_ids don't match WLT-XXXXXXXX"
    neg_amt = (df["amount_ngn"] < 0).sum()
    assert neg_amt == 0, f"Negative amounts: {neg_amt:,}"
    assert len(df) > 400_000, f"Sample too small: {len(df):,} rows"
    logger.info("Pre-load validation passed")


def run(force_resample: bool = False) -> None:
    """Full load pipeline: ingest → clean → sample → validate → load to Postgres."""
    engine = get_pg_engine()

    # Check if already loaded
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM fact_mobile_money_tx")).scalar()
    if existing > 0 and not force_resample:
        logger.info(f"fact_mobile_money_tx already has {existing:,} rows — skipping load")
        return

    # Ingest + clean
    df_raw   = ingest_parquet.load_raw()
    df_clean, report = clean_parquet.clean(df_raw)
    CLEANED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(CLEANED_PATH, index=False)
    logger.info(f"Saved cleaned parquet: {CLEANED_PATH}")

    # Build + save sample
    df_sample = build_sample(df_clean, SAMPLE_SIZE)
    df_sample.to_parquet(SAMPLE_PATH, index=False)
    logger.info(f"Saved 500K sample: {SAMPLE_PATH}")

    # Pre-load validation
    _validate_pre_load(df_sample)

    # Load fact table in chunks
    logger.info("Loading fact_mobile_money_tx...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_mobile_money_tx CASCADE"))

    df_sample.to_sql(
        "fact_mobile_money_tx",
        engine,
        if_exists="append",
        index=False,
        chunksize=CHUNKSIZE,
        method="multi",
    )
    logger.info("fact_mobile_money_tx loaded")

    # Load wallet agg dimension
    agg = _build_wallet_agg(df_sample)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dim_wallet_agg_mm CASCADE"))
    agg.to_sql(
        "dim_wallet_agg_mm",
        engine,
        if_exists="append",
        index=False,
        chunksize=CHUNKSIZE,
        method="multi",
    )
    logger.info(f"dim_wallet_agg_mm loaded: {len(agg):,} wallets")

    # Save audit
    audit = {
        "total_rows_loaded": len(df_sample),
        "wallet_agg_rows":   len(agg),
        "quality_report":    report,
    }
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, default=str))
    logger.info(f"Audit saved: {AUDIT_PATH}")

    with engine.connect() as conn:
        final = conn.execute(text("SELECT COUNT(*) FROM fact_mobile_money_tx")).scalar()
    logger.info(f"fact_mobile_money_tx final row count: {final:,}")
    assert abs(final - SAMPLE_SIZE) <= SAMPLE_SIZE * 0.01, \
        f"Final row count {final:,} deviates >1% from target {SAMPLE_SIZE:,}"


if __name__ == "__main__":
    run()
