import hashlib
import uuid
import numpy as np
import pandas as pd
from src.logging_setup import get_logger

logger = get_logger(__name__)

FINANCIAL_COLS = ["net_amount", "total_fee"]


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the XML transactions DataFrame per §6.5 rules.

    Actions (in order):
    1. Type casts: amounts → int64, is_verified → bool, timestamps → datetime64
    2. Regenerate UUIDs for duplicate receipt_numbers on TOP_UP rows
    3. Add is_ref_dup flag (reference_number shared across rows)
    4. Add date_order_anomaly flag (created_at > paying_at)
    5. SHA-256 hash phone_number
    6. IQR outlier flags on net_amount, total_fee

    Returns (cleaned_df, quality_report).
    """
    before = _stats(df)
    df = df.copy()
    actions = []

    # 1. Type casts
    for col in ["net_amount", "fee_internal_amount", "fee_external_amount", "total_fee"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
    df["is_verified"] = df["is_verified"].str.upper().map({"TRUE": True, "FALSE": False})
    for col in ["paying_at", "created_at", "updated_at"]:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    df["transaction_id"] = pd.to_numeric(df["transaction_id"], errors="coerce").astype("Int64")
    actions.append("Type casts: amounts→Int64, is_verified→bool, timestamps→datetime64, transaction_id→Int64")
    logger.info("Type casts applied")

    # 2. Regenerate UUIDs for all TOP_UP receipt_numbers (all are duplicated)
    top_up_mask = df["transaction_type"] == "TOP_UP"
    n_top_up = int(top_up_mask.sum())
    df.loc[top_up_mask, "receipt_number"] = [str(uuid.uuid4()) for _ in range(n_top_up)]
    dup_after = int(df["receipt_number"].duplicated().sum())
    actions.append(
        f"Regenerated {n_top_up:,} receipt_numbers for TOP_UP rows; "
        f"duplicates after: {dup_after}"
    )
    logger.info(f"UUID regen: {n_top_up:,} TOP_UP receipt_numbers replaced; {dup_after} dups remain")

    # 3. is_ref_dup flag
    df["is_ref_dup"] = df["reference_number"].duplicated(keep=False)
    n_ref_dup = int(df["is_ref_dup"].sum())
    actions.append(f"is_ref_dup flag: {n_ref_dup:,} rows share a reference_number")
    logger.info(f"is_ref_dup: {n_ref_dup:,} rows flagged")

    # 4. date_order_anomaly flag
    df["date_order_anomaly"] = df["created_at"] > df["paying_at"]
    n_anom = int(df["date_order_anomaly"].sum())
    actions.append(f"date_order_anomaly flag: {n_anom:,} rows where created_at > paying_at")
    logger.info(f"date_order_anomaly: {n_anom:,} rows flagged")

    # 5. SHA-256 hash phone_number
    def _sha256(val: str) -> str:
        if pd.isna(val):
            return None
        return hashlib.sha256(str(val).encode()).hexdigest()

    df["phone_number"] = df["phone_number"].apply(_sha256)
    actions.append("phone_number hashed with SHA-256")
    logger.info("phone_number SHA-256 hashed")

    # 6. IQR outlier flags
    for col in FINANCIAL_COLS:
        series = df[col].dropna().astype(float)
        q1, q3 = series.quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        flag = f"is_{col}_outlier"
        df[flag] = (df[col].astype(float) < lo) | (df[col].astype(float) > hi)
        n = int(df[flag].sum())
        actions.append(f"{col}: {n:,} outliers ({n/len(df)*100:.2f}%) → {flag}")
        logger.info(f"{col}: {n:,} outliers flagged")

    after = _stats(df)
    report = {
        "source":  "xml",
        "before":  before,
        "after":   after,
        "actions": actions,
    }
    logger.info(f"XML cleaning done: {before['row_count']:,} -> {after['row_count']:,} rows")
    return df, report


def _stats(df: pd.DataFrame) -> dict:
    return {
        "row_count":      len(df),
        "null_count":     int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "receipt_dup":    int(df["receipt_number"].duplicated().sum()) if "receipt_number" in df.columns else None,
    }
