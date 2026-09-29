from pathlib import Path
import sys
import os

# Backend root
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# Load environment variables if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv(BACKEND_DIR / ".env")
except ImportError:
    pass

from database.connection import engine
from database.base import Base

# Import ALL models so SQLAlchemy registers every table
from models.core import *
from models.citizen import *
from models.sources import *
from models.ai import *
from models.conflicts import *
from models.audit import *
from models.auth import *
from models.gis import *
from models.satellite import *

DATABASE_URL = str(engine.url)

print("=" * 60)
print("SYNCBHOOMI DATABASE RESET")
print("=" * 60)
print(f"Database: {DATABASE_URL}")

# Only allow SQLite reset
if not DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "This reset script is intended for SQLite only. "
        f"Current database: {DATABASE_URL}"
    )

# SQLite file location
db_path = BACKEND_DIR / "bhoomisync_arch.db"

# If database exists, remove it
if db_path.exists():
    print(f"Removing old database: {db_path}")
    db_path.unlink()

# Create all tables from current SQLAlchemy models
print("Creating database tables...")
Base.metadata.create_all(bind=engine)

print()
print("SUCCESS!")
print(f"New database created: {db_path}")
print()
print("Registered tables:")

for table_name in sorted(Base.metadata.tables.keys()):
    print(f"  ✓ {table_name}")

print()
print("Syncbhoomi database reset completed.")
print("=" * 60)