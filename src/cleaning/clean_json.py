import pandas as pd
from src.logging_setup import get_logger

logger = get_logger(__name__)


def clean(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Clean the customer profiles DataFrame per §6.5 rules.
    Returns (cleaned_df, quality_report).
    """
    before = _stats(df)
    df = df.copy()

    # Parse date columns
    df["date_of_birth"]    = pd.to_datetime(df["date_of_birth"],    errors="coerce")
    df["registration_date"] = pd.to_datetime(df["registration_date"], errors="coerce")

    # Normalise categoricals to lowercase for consistency
    for col in ["account_status", "referral_source", "support_tier",
                "gender", "preferred_language", "notification_preferences"]:
        if col in df.columns:
            df[col] = df[col].str.strip().str.lower()

    # age: assert in sensible range, flag anomalies
    if "age" in df.columns:
        df["is_age_anomaly"] = ~df["age"].between(10, 120)
        n = int(df["is_age_anomaly"].sum())
        if n:
            logger.warning(f"{n} age values outside [10, 120] — flagged as is_age_anomaly")

    # Missing value strategy (§6.5): source has zero nulls so nothing to impute;
    # add _is_missing sibling cols for any future schema additions
    null_cols = df.columns[df.isnull().any()].tolist()
    for col in null_cols:
        pct = df[col].isnull().mean() * 100
        if pct > 50:
            df.drop(columns=[col], inplace=True)
            logger.info(f"Dropped {col}: {pct:.1f}% missing (>50% threshold)")
        else:
            df[f"{col}_is_missing"] = df[col].isnull()
            logger.info(f"Flagged {col}: {pct:.1f}% missing -> {col}_is_missing added")

    after = _stats(df)
    report = {
        "source": "json",
        "before": before,
        "after":  after,
        "actions": [
            "date_of_birth → datetime64",
            "registration_date → datetime64",
            "Lowercased: account_status, referral_source, support_tier, gender, preferred_language, notification_preferences",
            "is_age_anomaly flag added",
        ],
    }
    logger.info(f"JSON cleaning done: {before['row_count']:,} -> {after['row_count']:,} rows")
    return df, report


def _stats(df: pd.DataFrame) -> dict:
    return {
        "row_count":      len(df),
        "null_count":     int(df.isnull().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "col_null_pct":   (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
    }
