import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pymongo import MongoClient

load_dotenv()

POSTGRES_URL = os.getenv(
    "POSTGRES_URL",
    "postgresql://neondb_owner:npg_o6mavRV7DucE@ep-young-hill-amjgu6t0.c-5.us-east-1.aws.neon.tech/neondb?sslmode=require",
)
MONGODB_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://retainiq_admin:RetainIQ2026SecurePass@cluster0.sekfgbi.mongodb.net/?appName=Cluster0",
)
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "retainiq")


def get_pg_engine():
    return create_engine(POSTGRES_URL, pool_pre_ping=True)


def get_mongo_db():
    client = MongoClient(MONGODB_URI)
    return client[MONGODB_DB_NAME]
