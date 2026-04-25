"""
Creates all Postgres tables and indexes for the RetainIQ pipeline.
Safe to run multiple times (uses IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
"""
from sqlalchemy import text
from src.config import get_pg_engine
from src.logging_setup import get_logger

logger = get_logger(__name__)

DDL = """
-- ─────────────────────────────────────────────────────────────────────────────
-- FACT TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fact_mobile_money_tx (
    transaction_id          VARCHAR(60)     PRIMARY KEY,
    wallet_id               VARCHAR(20)     NOT NULL,
    timestamp               TIMESTAMPTZ,
    transaction_type        VARCHAR(20),
    amount_ngn              NUMERIC(15,2),
    fee_ngn                 NUMERIC(10,2),
    balance_after_ngn       NUMERIC(18,2),
    agent_id                VARCHAR(60),
    channel                 VARCHAR(20),
    device_os               VARCHAR(20),
    kyc_tier                VARCHAR(10),
    fraud_flag              BOOLEAN,
    churn_30d               BOOLEAN,
    is_amount_ngn_outlier         BOOLEAN DEFAULT FALSE,
    is_fee_ngn_outlier            BOOLEAN DEFAULT FALSE,
    is_balance_after_ngn_outlier  BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS fact_xml_transactions (
    transaction_id          BIGINT          PRIMARY KEY,
    status                  VARCHAR(5),
    reference_number        VARCHAR(60),
    partner_reference_number VARCHAR(60),
    capture_number          VARCHAR(60),
    receipt_number          VARCHAR(60)     UNIQUE,
    customer_id             VARCHAR(20),
    wallet_id               VARCHAR(20)     NOT NULL,
    phone_number            VARCHAR(64),
    created_by              VARCHAR(20),
    transaction_type        VARCHAR(20),
    journal_type            VARCHAR(10),
    category                VARCHAR(50),
    currency                VARCHAR(5)      DEFAULT 'IDR',
    net_amount              BIGINT,
    fee_internal_amount     BIGINT,
    fee_external_amount     BIGINT,
    total_fee               BIGINT,
    channel                 VARCHAR(20),
    channel_reference_number VARCHAR(60),
    is_verified             BOOLEAN,
    note                    TEXT,
    detail                  TEXT,
    paying_at               TIMESTAMPTZ,
    created_at              TIMESTAMPTZ,
    updated_at              TIMESTAMPTZ,
    is_ref_dup              BOOLEAN         DEFAULT FALSE,
    date_order_anomaly      BOOLEAN         DEFAULT FALSE,
    is_net_amount_outlier   BOOLEAN         DEFAULT FALSE,
    is_total_fee_outlier    BOOLEAN         DEFAULT FALSE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- DIMENSION TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim_wallet_agg_mm (
    wallet_id               VARCHAR(20)     PRIMARY KEY,
    total_tx_count          INTEGER,
    total_volume_ngn        NUMERIC(20,2),
    total_fees_ngn          NUMERIC(15,2),
    avg_tx_amount           NUMERIC(15,2),
    first_tx_date           DATE,
    last_tx_date            DATE,
    dominant_channel        VARCHAR(20),
    dominant_tx_type        VARCHAR(20),
    fraud_flag              BOOLEAN,
    churn_30d               BOOLEAN
);

CREATE TABLE IF NOT EXISTS dim_wallet_agg_xml (
    wallet_id               VARCHAR(20)     PRIMARY KEY,
    xml_tx_count            INTEGER,
    xml_total_volume        BIGINT,
    xml_total_fees          BIGINT,
    xml_first_tx_date       DATE,
    xml_last_tx_date        DATE
);

CREATE TABLE IF NOT EXISTS dim_unified_wallet (
    wallet_id               VARCHAR(20)     PRIMARY KEY,
    full_name               VARCHAR(120),
    age                     SMALLINT,
    gender                  VARCHAR(10),
    state                   VARCHAR(60),
    city                    VARCHAR(80),
    registration_date       DATE,
    account_status          VARCHAR(20),
    preferred_language      VARCHAR(30),
    linked_bank             VARCHAR(60),
    support_tier            VARCHAR(20),
    kyc_tier                VARCHAR(10),
    acquisition_channel     VARCHAR(40),
    has_xml_activity        BOOLEAN         DEFAULT FALSE,
    total_tx_count          INTEGER,
    total_volume_ngn        NUMERIC(20,2),
    total_fees_ngn          NUMERIC(15,2),
    avg_tx_amount           NUMERIC(15,2),
    first_tx_date           DATE,
    last_tx_date            DATE,
    dominant_channel        VARCHAR(20),
    dominant_tx_type        VARCHAR(20),
    fraud_flag              BOOLEAN,
    churn_30d               BOOLEAN
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_mmtx_wallet    ON fact_mobile_money_tx (wallet_id);
CREATE INDEX IF NOT EXISTS idx_mmtx_ts        ON fact_mobile_money_tx (timestamp);
CREATE INDEX IF NOT EXISTS idx_mmtx_type      ON fact_mobile_money_tx (transaction_type);
CREATE INDEX IF NOT EXISTS idx_mmtx_fraud     ON fact_mobile_money_tx (fraud_flag) WHERE fraud_flag = TRUE;
CREATE INDEX IF NOT EXISTS idx_mmtx_churn     ON fact_mobile_money_tx (churn_30d)  WHERE churn_30d  = TRUE;
CREATE INDEX IF NOT EXISTS idx_mmtx_kyc       ON fact_mobile_money_tx (kyc_tier);

CREATE INDEX IF NOT EXISTS idx_xml_wallet     ON fact_xml_transactions (wallet_id);
CREATE INDEX IF NOT EXISTS idx_xml_type       ON fact_xml_transactions (transaction_type);
CREATE INDEX IF NOT EXISTS idx_xml_paying     ON fact_xml_transactions (paying_at);

CREATE INDEX IF NOT EXISTS idx_unified_status ON dim_unified_wallet (account_status);
CREATE INDEX IF NOT EXISTS idx_unified_kyc    ON dim_unified_wallet (kyc_tier);
CREATE INDEX IF NOT EXISTS idx_unified_churn  ON dim_unified_wallet (churn_30d) WHERE churn_30d = TRUE;
"""


def create_all(drop_first: bool = False) -> None:
    """Create all tables and indexes. Set drop_first=True to rebuild from scratch."""
    engine = get_pg_engine()
    with engine.begin() as conn:
        if drop_first:
            _drop_all(conn)
        logger.info("Creating tables...")
        for stmt in DDL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        logger.info("Creating indexes...")
        for stmt in INDEXES.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
    logger.info("Postgres schema ready")


def _drop_all(conn) -> None:
    tables = [
        "dim_unified_wallet", "dim_wallet_agg_mm", "dim_wallet_agg_xml",
        "fact_mobile_money_tx", "fact_xml_transactions",
    ]
    for t in tables:
        conn.execute(text(f"DROP TABLE IF EXISTS {t} CASCADE"))
        logger.info(f"Dropped {t}")


if __name__ == "__main__":
    create_all()
