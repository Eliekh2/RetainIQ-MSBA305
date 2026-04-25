import numpy as np
import pandas as pd
from src.logging_setup import get_logger

logger = get_logger(__name__)

FINANCIAL_COLS = ["amount_ngn", "fee_ngn", "balance_after_ngn"]
CASHIN_CASHOUT = {"cashin", "cashout"}


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the raw parquet DataFrame per §6.5 rules.
    Returns (cleaned_df, quality_report).
    """
    before = _stats(df)
    df = df.copy()

    # Type coercions
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["fraud_flag"] = df["fraud_flag"].astype(bool)
    df["churn_30d"]  = df["churn_30d"].astype(bool)

    # agent_id: empty string → None for non-cashin/cashout rows
    non_agent = ~df["transaction_type"].isin(CASHIN_CASHOUT)
    df.loc[non_agent & (df["agent_id"].fillna("") == ""), "agent_id"] = None
    logger.info(f"agent_id nulled for {(non_agent & (df['agent_id'].isna())).sum():,} non-agent rows")

    # IQR outlier flags — flag, never remove
    for col in FINANCIAL_COLS:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        flag = f"is_{col}_outlier"
        df[flag] = (df[col] < lo) | (df[col] > hi)
        n = int(df[flag].sum())
        logger.info(f"{col}: {n:,} outliers ({n/len(df)*100:.2f}%) flagged as {flag}")

    after = _stats(df)
    report = {
        "source": "parquet",
        "before": before,
        "after":  after,
        "actions": [
            "Coerced timestamp → datetime64",
            "Coerced fraud_flag, churn_30d → bool",
            "agent_id empty string → NULL for non-cashin/cashout rows",
            f"IQR outlier flags added for: {FINANCIAL_COLS}",
        ],
    }
    logger.info(f"Parquet cleaning done: {before['row_count']:,} -> {after['row_count']:,} rows")
    return df, report


def _stats(df: pd.DataFrame) -> dict:
    return {
        "row_count":      len(df),
        "null_count":     int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "col_null_pct":   (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
    }
