"""
Loads cleaned XML transactions into fact_xml_transactions and dim_wallet_agg_xml.
"""
import json
from pathlib import Path
import pandas as pd
from sqlalchemy import text
from src.config import get_pg_engine
from src.ingestion import ingest_xml
from src.cleaning import clean_xml
from src.logging_setup import get_logger

logger = get_logger(__name__)

PROCESSED_PATH = Path("data/processed/xml_final.parquet")
AUDIT_PATH     = Path("data/audit/xml_load_audit.json")
EXPECTED_ROWS  = 28_360
CHUNKSIZE      = 5_000


def _build_wallet_agg(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby("wallet_id").agg(
        xml_tx_count     =("transaction_id", "count"),
        xml_total_volume =("net_amount",     "sum"),
        xml_total_fees   =("total_fee",      "sum"),
        xml_first_tx_date=("paying_at",      "min"),
        xml_last_tx_date =("paying_at",      "max"),
    ).reset_index()
    agg["xml_first_tx_date"] = pd.to_datetime(agg["xml_first_tx_date"]).dt.date
    agg["xml_last_tx_date"]  = pd.to_datetime(agg["xml_last_tx_date"]).dt.date
    return agg


def _validate_pre_load(df: pd.DataFrame) -> None:
    dup_pk = df["transaction_id"].duplicated().sum()
    assert dup_pk == 0, f"PK violation: {dup_pk:,} duplicate transaction_ids"
    dup_receipt = df["receipt_number"].duplicated().sum()
    assert dup_receipt == 0, f"UNIQUE violation: {dup_receipt:,} duplicate receipt_numbers after cleaning"
    bad_wlt = (~df["wallet_id"].str.match(r'^WLT-\d{8}$', na=False)).sum()
    assert bad_wlt == 0, f"FK format: {bad_wlt:,} bad wallet_ids"
    neg = (df["net_amount"].dropna() < 0).sum()
    assert neg == 0, f"Negative net_amount: {neg:,}"
    assert len(df) == EXPECTED_ROWS, f"Expected {EXPECTED_ROWS}, got {len(df)}"
    logger.info("XML pre-load validation passed")


def run(force_reload: bool = False) -> None:
    engine = get_pg_engine()

    with engine.connect() as conn:
        existing = conn.execute(text("SELECT COUNT(*) FROM fact_xml_transactions")).scalar()
    if existing > 0 and not force_reload:
        logger.info(f"fact_xml_transactions already has {existing:,} rows — skipping")
        return

    df_raw, batch_meta = ingest_xml.load_raw()
    df_clean, report   = clean_xml.clean(df_raw)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(PROCESSED_PATH, index=False)
    logger.info(f"Saved cleaned XML: {PROCESSED_PATH}")

    _validate_pre_load(df_clean)

    # Cast Int64 → int for SQLAlchemy compatibility
    for col in ["transaction_id", "net_amount", "fee_internal_amount", "fee_external_amount", "total_fee"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(object).where(df_clean[col].notna(), None)

    logger.info("Loading fact_xml_transactions...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE fact_xml_transactions CASCADE"))

    df_clean.to_sql(
        "fact_xml_transactions",
        engine,
        if_exists="append",
        index=False,
        chunksize=CHUNKSIZE,
        method="multi",
    )
    logger.info("fact_xml_transactions loaded")

    agg = _build_wallet_agg(df_clean)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE dim_wallet_agg_xml CASCADE"))
    agg.to_sql(
        "dim_wallet_agg_xml",
        engine,
        if_exists="append",
        index=False,
        chunksize=CHUNKSIZE,
        method="multi",
    )
    logger.info(f"dim_wallet_agg_xml loaded: {len(agg):,} wallets")

    audit = {"batch_meta": batch_meta, "rows_loaded": len(df_clean), "quality_report": report}
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, default=str))

    with engine.connect() as conn:
        final = conn.execute(text("SELECT COUNT(*) FROM fact_xml_transactions")).scalar()
    assert final == EXPECTED_ROWS, f"Final count {final} ≠ expected {EXPECTED_ROWS}"
    logger.info(f"fact_xml_transactions final count: {final:,}")


if __name__ == "__main__":
    run()
