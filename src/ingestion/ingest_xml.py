import re
from pathlib import Path
import xml.etree.ElementTree as ET
import pandas as pd
from src.logging_setup import get_logger

logger = get_logger(__name__)

RAW_PATH = Path("data/raw/ewallet_transactions.xml")
_WLT_RE = re.compile(r'^WLT-\d{8}$')


def load_raw(path: Path = RAW_PATH) -> tuple[pd.DataFrame, dict]:
    """Parse ewallet_transactions.xml. Returns (DataFrame, batch_metadata)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"XML not found: {path}")
    logger.info(f"Parsing XML: {path} ({path.stat().st_size / 1e6:.1f} MB)")

    tree = ET.parse(path)
    root = tree.getroot()

    header = root.find("batch_header")
    batch_meta = {
        "batch_id":         header.findtext("batch_id"),
        "source_system":    header.findtext("source_system"),
        "export_type":      header.findtext("export_type"),
        "generated_at":     header.findtext("generated_at"),
        "record_count":     int(header.findtext("record_count")),
        "total_wallets":    int(header.findtext("total_wallets")),
        "currency_default": header.findtext("currency_default"),
        "schema_version":   header.findtext("schema_version"),
    }
    logger.info(f"Batch: {batch_meta['batch_id']} | "
                f"{batch_meta['record_count']:,} records | "
                f"{batch_meta['total_wallets']} wallets")

    transactions = root.find("transactions")
    records = [_parse_tx(tx) for tx in transactions]
    df = pd.DataFrame(records)
    logger.info(f"Parsed {len(df):,} rows × {len(df.columns)} cols")
    _validate(df, batch_meta)
    return df, batch_meta


def _parse_tx(tx: ET.Element) -> dict:
    """Flatten one <transaction> element into a dict."""
    type_el = tx.find("classification/type")
    amt_el  = tx.find("financials/amount")
    return {
        "transaction_id":  tx.get("id"),
        "status":          tx.get("status"),
        "reference_number":         tx.findtext("identifiers/reference_number"),
        "partner_reference_number": tx.findtext("identifiers/partner_reference_number"),
        "capture_number":           tx.findtext("identifiers/capture_number"),
        "receipt_number":           tx.findtext("identifiers/receipt_number"),
        "customer_id":  tx.findtext("customer/customer_id"),
        "wallet_id":    tx.findtext("customer/wallet_id"),
        "phone_number": tx.findtext("customer/phone_number"),
        "created_by":   tx.findtext("customer/created_by"),
        "transaction_type": type_el.get("code") if type_el is not None else None,
        "journal_type":     type_el.findtext("journal_type") if type_el is not None else None,
        "category":     tx.findtext("classification/category"),
        "currency":     amt_el.get("currency", "IDR") if amt_el is not None else "IDR",
        "net_amount":            tx.findtext("financials/amount/net_amount"),
        "fee_internal_amount":   tx.findtext("financials/fees/fee_internal_amount"),
        "fee_external_amount":   tx.findtext("financials/fees/fee_external_amount"),
        "total_fee":             tx.findtext("financials/fees/total_fee"),
        "channel":               tx.findtext("channel_info/channel"),
        "channel_reference_number": tx.findtext("channel_info/channel_reference_number"),
        "is_verified":  tx.findtext("channel_info/is_verified"),
        "note":         tx.findtext("metadata/note"),
        "detail":       tx.findtext("metadata/detail"),
        "paying_at":    tx.findtext("timestamps/paying_at"),
        "created_at":   tx.findtext("timestamps/created_at"),
        "updated_at":   tx.findtext("timestamps/updated_at"),
    }


def _validate(df: pd.DataFrame, meta: dict) -> None:
    if len(df) != meta["record_count"]:
        raise ValueError(
            f"Row count mismatch: expected {meta['record_count']:,}, got {len(df):,}"
        )
    actual_wallets = df["wallet_id"].nunique()
    if actual_wallets != meta["total_wallets"]:
        raise ValueError(
            f"Wallet count mismatch: expected {meta['total_wallets']}, got {actual_wallets}"
        )
    bad_ids = (~df["wallet_id"].str.match(_WLT_RE, na=False)).sum()
    if bad_ids:
        raise ValueError(f"{bad_ids:,} wallet_ids don't match WLT-XXXXXXXX")
    logger.info("XML validation passed")
