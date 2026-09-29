from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
if load_dotenv:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./bhoomisync_arch.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine: Engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)


def database_status() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        postgis = "unavailable"
        if engine.dialect.name == "postgresql":
            with engine.connect() as connection:
                postgis = "available" if connection.exec_driver_sql("SELECT PostGIS_Version()").scalar() else "unavailable"
        return {"database": "connected", "postgis": postgis}
    except Exception:
        return {"database": "unavailable", "postgis": "unavailable"}