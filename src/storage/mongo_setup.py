"""
Creates MongoDB collections and indexes for the RetainIQ pipeline.
Safe to run multiple times (index creation is idempotent with MongoDB).
"""
from pymongo import ASCENDING, DESCENDING, MongoClient
from src.config import get_mongo_db
from src.logging_setup import get_logger

logger = get_logger(__name__)

COLLECTION = "customer_profiles"


def create_all() -> None:
    """Create collection and indexes on MongoDB Atlas."""
    db = get_mongo_db()
    col = db[COLLECTION]

    indexes = [
        ([("wallet_id", ASCENDING)],  {"unique": True, "name": "idx_wallet_id_unique"}),
        ([("account_status", ASCENDING)], {"name": "idx_account_status"}),
        ([("kyc_tier", ASCENDING)],    {"name": "idx_kyc_tier"}),
        ([("state", ASCENDING)],       {"name": "idx_state"}),
        ([("registration_date", ASCENDING)], {"name": "idx_registration_date"}),
    ]

    for keys, opts in indexes:
        col.create_index(keys, **opts)
        logger.info(f"Index created/verified: {opts['name']}")

    logger.info(f"MongoDB collection '{COLLECTION}' ready with {len(indexes)} indexes")


def drop_collection() -> None:
    """Drop and recreate the customer_profiles collection."""
    db = get_mongo_db()
    db[COLLECTION].drop()
    logger.info(f"Dropped collection: {COLLECTION}")


if __name__ == "__main__":
    create_all()
