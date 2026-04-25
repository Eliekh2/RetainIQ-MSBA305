import re
from pathlib import Path
import pandas as pd
from src.logging_setup import get_logger

logger = get_logger(__name__)

RAW_PATH = Path("data/raw/raw_mobile_money.parquet")
_WLT_RE = re.compile(r'^WLT-\d{8}$')

REQUIRED_COLS = {
    "transaction_id", "wallet_id", "timestamp", "transaction_type",
    "amount_ngn", "fee_ngn", "balance_after_ngn", "agent_id",
    "channel", "device_os", "kyc_tier", "fraud_flag", "churn_30d",
}


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Load raw_mobile_money.parquet and validate structure."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Parquet not found: {path}")
    logger.info(f"Loading parquet: {path}")
    df = pd.read_parquet(path)
    logger.info(f"Loaded {len(df):,} rows × {len(df.columns)} cols")
    _validate(df)
    return df


def _validate(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    bad_ids = (~df["wallet_id"].str.match(_WLT_RE)).sum()
    if bad_ids:
        raise ValueError(f"{bad_ids:,} wallet_ids don't match WLT-XXXXXXXX")
    dup_txn = df["transaction_id"].duplicated().sum()
    if dup_txn:
        logger.warning(f"{dup_txn:,} duplicate transaction_ids found")
    logger.info("Parquet validation passed")
