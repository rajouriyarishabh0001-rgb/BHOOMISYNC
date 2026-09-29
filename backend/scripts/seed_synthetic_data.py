"""Generate the CSV package and load the existing local SQLite demo register.

SYNTHETIC DEMO DATA - NOT OFFICIAL GOVERNMENT RECORDS
"""
from __future__ import annotations

from generate_synthetic_data import generate
from seed_demo_data import seed


if __name__ == "__main__":
    counts = generate()
    seed()
    print(f"Generated and loaded synthetic Syncbhoomi data: {counts}")
