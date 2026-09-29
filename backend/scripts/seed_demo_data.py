"""Deterministic synthetic data generator for the local BHOOMISYNC MVP."""
from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "bhoomisync.db"
random.seed(42)

FIRST_NAMES = ["Rahul", "Suresh", "Anita", "Priya", "Vikram", "Neha", "Amit", "Kavita", "Manoj", "Ritu"]
LAST_NAMES = ["Sharma", "Patel", "Verma", "Singh", "Jain", "Khan", "Gupta", "Mishra", "Joshi", "Mehta"]
LAND_USES = ["Residential", "Residential Plot", "Commercial", "Mixed Use", "Institutional"]
ZONES = ["Zone A", "Zone B", "Zone C", "Zone D"]
CITIES = [
    ("Bhopal", "Bhopal", 23.2599, 77.4126),
    ("Indore", "Indore", 22.7196, 75.8577),
    ("Vidisha", "Vidisha", 23.5250, 77.8081),
    ("Jabalpur", "Jabalpur", 23.1815, 79.9864),
    ("Gwalior", "Gwalior", 26.2183, 78.1828),
    ("Ujjain", "Ujjain", 23.1765, 75.7885),
    ("Sagar", "Sagar", 23.8388, 78.7378),
    ("Dewas", "Dewas", 22.9676, 76.0534),
]


def schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS properties (
            parcel_id TEXT PRIMARY KEY, survey_number TEXT, khasra_number TEXT,
            owner_name TEXT NOT NULL, co_owner_name TEXT, area_sq_m REAL NOT NULL,
            area_sq_ft REAL NOT NULL, land_use TEXT NOT NULL, property_type TEXT,
            address TEXT, ward INTEGER, zone TEXT, village TEXT, tehsil TEXT,
            district TEXT, state TEXT, pincode TEXT, latitude REAL, longitude REAL,
            municipal_id TEXT, registration_id TEXT, property_tax_id TEXT,
            gis_status TEXT, registration_status TEXT, tax_status TEXT,
            land_record_status TEXT, planning_zone TEXT, building_status TEXT,
            built_up_area REAL, year_of_construction INTEGER, road_access TEXT,
            water_connection TEXT, electricity_connection TEXT, property_status TEXT,
            record_created TEXT, last_updated TEXT, source_department TEXT,
            verification_status TEXT, conflict_status TEXT, match_score REAL
        );
        CREATE TABLE IF NOT EXISTS source_datasets (
            id TEXT PRIMARY KEY, department TEXT, dataset_name TEXT, record_count INTEGER,
            version TEXT, status TEXT, updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS revenue_records (
            source_record_id TEXT PRIMARY KEY, parcel_id TEXT, owner_name TEXT,
            area_original REAL, area_unit TEXT, department TEXT, dataset_id TEXT, dataset_version TEXT
        );
        CREATE TABLE IF NOT EXISTS registration_records (
            source_record_id TEXT PRIMARY KEY, parcel_id TEXT, party_names TEXT,
            registration_date TEXT, area_original REAL, department TEXT, dataset_id TEXT, dataset_version TEXT
        );
        CREATE TABLE IF NOT EXISTS municipal_records (
            source_record_id TEXT PRIMARY KEY, parcel_id TEXT, owner_name TEXT,
            address TEXT, ward INTEGER, built_up_area REAL, department TEXT, dataset_id TEXT, dataset_version TEXT
        );
        CREATE TABLE IF NOT EXISTS property_tax_records (
            source_record_id TEXT PRIMARY KEY, parcel_id TEXT, owner_name TEXT,
            assessment_year INTEGER, tax_amount REAL, tax_status TEXT, department TEXT, dataset_id TEXT, dataset_version TEXT
        );
        CREATE TABLE IF NOT EXISTS gis_parcels (
            source_record_id TEXT PRIMARY KEY, parcel_id TEXT, geometry TEXT, gis_area_sq_m REAL,
            crs TEXT, department TEXT, dataset_id TEXT, dataset_version TEXT
        );
        CREATE TABLE IF NOT EXISTS planning_records (
            source_record_id TEXT PRIMARY KEY, parcel_id TEXT, planning_zone TEXT,
            land_use TEXT, department TEXT, dataset_id TEXT, dataset_version TEXT
        );
        CREATE TABLE IF NOT EXISTS satellite_observations (
            id TEXT PRIMARY KEY, parcel_id TEXT, image_date TEXT, provider TEXT, tile_url TEXT,
            analysis_status TEXT, land_cover TEXT, built_up_percentage REAL,
            vegetation_percentage REAL, water_percentage REAL, change_detected INTEGER,
            change_confidence REAL, analysis_summary TEXT
        );
        CREATE TABLE IF NOT EXISTS conflicts (
            id TEXT PRIMARY KEY, parcel_id TEXT, conflict_type TEXT, severity TEXT,
            description TEXT, status TEXT, source_department TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS record_matches (
            id TEXT PRIMARY KEY, parcel_id TEXT, match_score REAL, confidence_level TEXT,
            explanation TEXT, factors TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS record_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, field_name TEXT,
            old_value TEXT, new_value TEXT, changed_by TEXT, department TEXT,
            changed_at TEXT, reason TEXT, version_number INTEGER
        );
        CREATE TABLE IF NOT EXISTS verification_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, parcel_id TEXT, status TEXT,
            verified_by TEXT, department TEXT, reason TEXT, created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, record_id TEXT,
            actor TEXT, role TEXT, department TEXT, details TEXT, created_at TEXT
        );
        """
    )


def seed() -> None:
    connection = sqlite3.connect(DB_PATH)
    schema(connection)
    for table in ["properties", "source_datasets", "revenue_records", "registration_records", "municipal_records", "property_tax_records", "gis_parcels", "planning_records", "satellite_observations", "conflicts", "record_matches", "record_versions", "verification_records", "audit_logs"]:
        connection.execute(f"DELETE FROM {table}")

    now = datetime(2026, 9, 9)
    departments = [("Revenue", 1000), ("Registration", 950), ("Municipal", 980), ("Property Tax", 940), ("GIS", 1000), ("Planning", 900), ("Satellite", 800)]
    for department, count in departments:
        connection.execute("INSERT INTO source_datasets VALUES (?, ?, ?, ?, ?, ?, ?)", (f"DS-{department[:3].upper()}", department, f"{department} urban register", count, "v1.0", "READY", now.isoformat()))

    for index in range(1000):
        parcel_id = f"P{1001 + index}"
        first, last = FIRST_NAMES[index % len(FIRST_NAMES)], LAST_NAMES[(index // len(FIRST_NAMES)) % len(LAST_NAMES)]
        owner = f"{first} {last}"
        area = round(70 + ((index * 37) % 1600) + random.random(), 2)
        city, district, city_lat, city_lon = CITIES[index % len(CITIES)]
        lat = city_lat + ((index // len(CITIES)) % 25 - 12) * 0.0011
        lon = city_lon + ((index // len(CITIES)) // 25) * 0.0014
        ward = index % 12 + 1
        land_use = LAND_USES[index % len(LAND_USES)]
        status = ["VERIFIED", "AI_MATCHED", "REQUIRES_REVIEW", "NEW"][index % 4]
        conflict_status = "OPEN" if index % 10 == 0 else "NONE"
        score = round(0.94 - (index % 7) * 0.018, 3)
        created = (now - timedelta(days=400 - index % 365)).date().isoformat()
        values = (parcel_id, f"SUR-{20000 + index}", f"KHA-{50000 + index}", owner, None, area, round(area * 10.7639, 2), land_use, "Urban Parcel", f"{ward} Civil Lines, {city}", ward, ZONES[index % 4], f"{city} Urban", city, district, "Madhya Pradesh", f"46{4000 + index % 1000}", lat, lon, f"M{1001 + index}", f"REG{1001 + index}", f"T{1001 + index}", "AVAILABLE", "REGISTERED", "PAID" if index % 3 else "DUE", "CURRENT", f"{ZONES[index % 4]} / {land_use}", "Built-up" if index % 3 else "Open", round(area * 0.65, 2), 1990 + index % 35, "Available", "Yes" if index % 2 else "No", "Yes", "ACTIVE", created, now.isoformat(), "HARMONIZED PROPERTY REGISTER", status, conflict_status, score)
        connection.execute("INSERT INTO properties VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", values)
        if index < 1000:
            connection.execute("INSERT INTO revenue_records VALUES (?,?,?,?,?,?,?,?)", (f"R{1001 + index}", parcel_id, owner if index % 9 else f"{first[0]}. {last}", area * 10.7639 if index % 5 else area, "sq.ft" if index % 5 else "sq.m", "Revenue", "DS-REV", "v1.0"))
        if index < 950:
            connection.execute("INSERT INTO registration_records VALUES (?,?,?,?,?,?,?,?)", (f"REG{1001 + index}", parcel_id, json.dumps([owner]), (now - timedelta(days=index % 1800)).date().isoformat(), area * (1.02 if index % 11 == 0 else 1), "Registration", "DS-REG", "v1.0"))
        if index < 980:
            connection.execute("INSERT INTO municipal_records VALUES (?,?,?,?,?,?,?,?,?)", (f"M{1001 + index}", parcel_id, owner, f"{ward} Civil Lines, Vidisha", ward, area * .65, "Municipal", "DS-MUN", "v1.0"))
        if index < 940:
            connection.execute("INSERT INTO property_tax_records VALUES (?,?,?,?,?,?,?,?,?)", (f"T{1001 + index}", parcel_id, owner, 2026, round(area * 4.3, 2), "DUE" if index % 3 == 0 else "PAID", "Property Tax", "DS-PRO", "v1.0"))
        geometry = {"type": "Polygon", "coordinates": [[[lon, lat], [lon + .001, lat], [lon + .001, lat + .001], [lon, lat + .001], [lon, lat]]]}
        connection.execute("INSERT INTO gis_parcels VALUES (?,?,?,?,?,?,?,?)", (f"GIS{1001 + index}", parcel_id, json.dumps(geometry), area * (1.01 if index % 13 == 0 else 1), "EPSG:4326", "GIS", "DS-GIS", "v1.0"))
        if index < 900:
            connection.execute("INSERT INTO planning_records VALUES (?,?,?,?,?,?,?)", (f"PL{1001 + index}", parcel_id, ZONES[index % 4], land_use, "Planning", "DS-PLA", "v1.0"))
        if index < 800:
            built = round(55 + (index * 17) % 38, 1)
            connection.execute("INSERT INTO satellite_observations VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (f"SAT{1001 + index}", parcel_id, "2026-08-15", "DEMO_PROVIDER", "", "DEMO_ANALYSIS", "Built-up / Open", built, round(100 - built - 8, 1), 8.0, 1 if index % 6 == 0 else 0, round(.78 + (index % 15) / 100, 2), "Demo visual analysis only; field verification required."))
        if index % 10 == 0:
            conflict_type = ["OWNER_VARIATION", "AREA_MISMATCH", "GIS_BOUNDARY_VARIANCE"][index % 3]
            connection.execute("INSERT INTO conflicts VALUES (?,?,?,?,?,?,?,?)", (f"C-{parcel_id}", parcel_id, conflict_type, "HIGH" if index % 30 == 0 else "MEDIUM", "Potential inconsistency detected. Manual verification required.", "OPEN", "DEMO HARMONIZED VIEW", now.isoformat()))
        factors = {"owner_similarity": 0.96, "parcel_similarity": 1.0, "survey_similarity": .92, "address_similarity": .88, "area_similarity": .97, "landuse_similarity": 1.0, "gis_similarity": .91}
        explanation = "Same parcel ID; owner names highly similar; area and land use are aligned; GIS comparison is within demo tolerance."
        connection.execute("INSERT INTO record_matches VALUES (?,?,?,?,?,?,?)", (f"MATCH-{parcel_id}", parcel_id, score, "HIGH" if score >= .9 else "MEDIUM", explanation, json.dumps(factors), now.isoformat()))
    connection.commit()
    connection.close()
    print(f"Seeded 1000 properties and separate departmental datasets into {DB_PATH}")


if __name__ == "__main__":
    seed()
