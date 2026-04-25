import json
import re
from pathlib import Path
import pandas as pd
from src.logging_setup import get_logger

logger = get_logger(__name__)

RAW_PATH = Path("data/raw/customer_profiles.json")
_WLT_RE = re.compile(r'^WLT-\d{8}$')


def load_raw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Load customer_profiles.json and return flat DataFrame."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")
    logger.info(f"Loading JSON: {path} ({path.stat().st_size / 1e6:.1f} MB)")
    try:
        with open(path, "r", encoding="utf-8") as f:
            wrapper = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON: {e}") from e

    if "data" not in wrapper:
        raise ValueError("JSON wrapper missing 'data' key")

    records = wrapper["data"]
    expected = wrapper.get("records_total", len(records))
    logger.info(f"Metadata reports {expected:,} records; found {len(records):,}")

    df = pd.DataFrame(records)
    logger.info(f"Shape after normalize: {df.shape}")
    _validate(df, expected)
    return df


def get_metadata(path: Path = RAW_PATH) -> dict:
    """Return the JSON wrapper metadata (excluding the data array)."""
    with open(path, "r", encoding="utf-8") as f:
        wrapper = json.load(f)
    return {k: v for k, v in wrapper.items() if k != "data"}


def _validate(df: pd.DataFrame, expected_count: int) -> None:
    if abs(len(df) - expected_count) > expected_count * 0.01:
        raise ValueError(
            f"Record count mismatch: expected {expected_count:,}, got {len(df):,}"
        )
    if "wallet_id" not in df.columns:
        raise ValueError("wallet_id column missing from JSON data")
    bad_ids = (~df["wallet_id"].str.match(_WLT_RE)).sum()
    if bad_ids:
        raise ValueError(f"{bad_ids:,} wallet_ids don't match WLT-XXXXXXXX")
    dup_wlt = df["wallet_id"].duplicated().sum()
    if dup_wlt:
        raise ValueError(f"{dup_wlt:,} duplicate wallet_ids in profiles (expected 0)")
    logger.info("JSON validation passed")
