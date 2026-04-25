"""
Loads cleaned customer profiles into MongoDB Atlas customer_profiles collection.
"""
import json
from pathlib import Path
import pandas as pd
from src.config import get_mongo_db
from src.ingestion import ingest_json
from src.cleaning import clean_json
from src.logging_setup import get_logger

logger = get_logger(__name__)

COLLECTION     = "customer_profiles"
CLEANED_PATH   = Path("data/processed/json_cleaned.json")
AUDIT_PATH     = Path("data/audit/json_load_audit.json")
BATCH_SIZE     = 5_000


def _validate_pre_load(df: pd.DataFrame) -> None:
    dup = df["wallet_id"].duplicated().sum()
    assert dup == 0, f"Duplicate wallet_ids: {dup:,}"
    bad = (~df["wallet_id"].str.match(r'^WLT-\d{8}$')).sum()
    assert bad == 0, f"Bad wallet_id format: {bad:,}"
    assert len(df) > 300_000, f"Too few profiles: {len(df):,}"
    logger.info("JSON pre-load validation passed")


def _df_to_docs(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame rows to Mongo documents. Renames _id-safe key."""
    records = df.to_dict(orient="records")
    for rec in records:
        rec["_id"] = rec.pop("wallet_id")
        # Convert NaT/NaN to None for Mongo
        for k, v in rec.items():
            if hasattr(v, "isoformat"):
                rec[k] = v.isoformat()
            elif pd.isna(v) if not isinstance(v, (list, dict)) else False:
                rec[k] = None
    return records


def run(force_reload: bool = False) -> None:
    db  = get_mongo_db()
    col = db[COLLECTION]

    existing = col.count_documents({})
    if existing > 0 and not force_reload:
        logger.info(f"customer_profiles already has {existing:,} docs — skipping")
        return

    df_raw          = ingest_json.load_raw()
    df_clean, report = clean_json.clean(df_raw)
    _validate_pre_load(df_clean)

    # Save cleaned snapshot
    CLEANED_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_json(CLEANED_PATH, orient="records", lines=True, force_ascii=False)
    logger.info(f"Saved cleaned JSON: {CLEANED_PATH}")

    if force_reload:
        col.drop()
        logger.info("Dropped existing collection for reload")

    docs = _df_to_docs(df_clean)
    logger.info(f"Inserting {len(docs):,} documents in batches of {BATCH_SIZE}...")

    inserted = 0
    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        col.insert_many(batch, ordered=False)
        inserted += len(batch)
        if inserted % 50_000 == 0:
            logger.info(f"  {inserted:,} / {len(docs):,} inserted")

    final = col.count_documents({})
    logger.info(f"customer_profiles final count: {final:,}")

    audit = {"docs_loaded": final, "quality_report": report}
    AUDIT_PATH.write_text(json.dumps(audit, indent=2, default=str))
    logger.info(f"Audit saved: {AUDIT_PATH}")


if __name__ == "__main__":
    run()
