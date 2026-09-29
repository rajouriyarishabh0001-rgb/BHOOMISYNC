"""Validate the generated Syncbhoomi CSV package.

SYNTHETIC DEMO DATA - NOT OFFICIAL GOVERNMENT RECORDS
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from generate_synthetic_data import DATA_DIR, FIELDS


def rows(name: str) -> list[dict]:
    with (DATA_DIR / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    errors: list[str] = []
    loaded = {name: rows(name) for name in FIELDS}
    properties = loaded["properties.csv"]
    property_ids = {row["property_id"] for row in properties}
    if len(properties) != 1000 or property_ids != {f"P{number}" for number in range(1001, 2001)}:
        errors.append("properties.csv must contain exactly P1001-P2000")
    persons = loaded["persons.csv"]
    if len(persons) != 200 or {row["person_id"] for row in persons} != {f"PERSON-{number:03d}" for number in range(1, 201)}:
        errors.append("persons.csv must contain exactly PERSON-001 to PERSON-200")
    for name, data in loaded.items():
        if any(row.get("data_type") != "SYNTHETIC DEMO DATA — NOT OFFICIAL GOVERNMENT RECORDS" for row in data):
            errors.append(f"{name} contains an unmarked row")
        for key in ("property_id", "parcel_id"):
            if data and key in data[0] and any(row[key] not in property_ids for row in data):
                errors.append(f"{name} contains a missing {key} reference")
        ids = []
        for row in data:
            identifier = next((row.get(key) for key in ("property_id", "person_id", "source_record_id", "registration_id", "municipal_record_id", "tax_record_id", "gis_record_id", "planning_record_id", "observation_id", "match_id", "conflict_id", "verification_id", "audit_id") if row.get(key)), None)
            if identifier: ids.append(identifier)
        if len(ids) != len(set(ids)): errors.append(f"{name} contains duplicate identifiers")
    for row in properties + loaded["gis_records.csv"]:
        try:
            geometry = json.loads(row["geometry"])
            if geometry.get("type") != "Polygon" or len(geometry["coordinates"][0]) < 4 or geometry["coordinates"][0][0] != geometry["coordinates"][0][-1]:
                errors.append(f"Invalid closed polygon in {row.get('property_id')}")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            errors.append(f"Invalid GeoJSON in {row.get('property_id')}")
    expected = {"revenue_records.csv": 1000, "registration_records.csv": 950, "municipal_records.csv": 980, "property_tax_records.csv": 940, "gis_records.csv": 1000, "planning_records.csv": 900, "satellite_observations.csv": 800}
    for name, count in expected.items():
        if len(loaded[name]) != count: errors.append(f"{name} expected {count}, found {len(loaded[name])}")
    if errors:
        raise SystemExit("Validation failed:\n- " + "\n- ".join(errors))
    print(f"Validated {len(properties)} properties, {len(persons)} persons and {sum(map(len, loaded.values()))} total CSV rows.")


if __name__ == "__main__":
    main()
