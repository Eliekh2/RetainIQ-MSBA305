import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from src.config import get_pg_engine, get_mongo_db

def test_postgres_connection():
    engine = get_pg_engine()
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1")).scalar()
    assert result == 1, f"Expected 1, got {result}"

def test_mongo_connection():
    db = get_mongo_db()
    result = db.client.admin.command("ping")
    assert result.get("ok") == 1.0, f"Mongo ping failed: {result}"
