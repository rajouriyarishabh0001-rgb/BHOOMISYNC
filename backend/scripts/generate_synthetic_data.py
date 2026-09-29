"""Generate reproducible Syncbhoomi synthetic CSV datasets.

SYNTHETIC DEMO DATA - NOT OFFICIAL GOVERNMENT RECORDS
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SEED = 20260910
DISCLAIMER = "SYNTHETIC DEMO DATA — NOT OFFICIAL GOVERNMENT RECORDS"
LAND_USES = ["Residential", "Commercial", "Industrial", "Agricultural", "Institutional", "Mixed Use", "Vacant Land", "Public/Semi-Public"]
NAMES = ["Rahul Sharma", "Amit Verma", "Neha Patel", "Priya Singh", "Suresh Yadav", "Anjali Jain", "Vikram Mehta", "Kavita Joshi", "Manoj Gupta", "Ritu Mishra", "Arjun Malviya", "Pooja Thakur", "Nitin Saxena", "Meera Chouhan", "Deepak Tiwari", "Sunita Rathore", "Karan Dubey", "Isha Kulkarni", "Mohan Solanki", "Rekha Bansal"]
VILLAGES = ["Vidisha Urban", "Sanchi Road", "Betwa Nagar", "Ganj Basoda Road", "Civil Lines Extension", "Kachhi Khedi", "Madhav Nagar", "Raisen Link"]
TRANSACTIONS = ["SALE", "GIFT", "INHERITANCE", "LEASE", "TRANSFER"]
TAX_STATUSES = ["PAID", "PARTIALLY_PAID", "PENDING", "OVERDUE"]
CONFLICT_TYPES = ["OWNER_MISMATCH", "OWNER_VARIATION", "AREA_MISMATCH", "LAND_USE_MISMATCH", "PARCEL_MISMATCH", "GIS_BOUNDARY_VARIANCE", "MISSING_SOURCE", "DUPLICATE_RECORD", "SATELLITE_CHANGE"]
FIELDS = {
    "persons.csv": ["person_id", "full_name", "phone", "email", "address", "village", "ward", "tehsil", "district", "state", "pincode", "data_type"],
    "properties.csv": ["property_id", "parcel_id", "person_id", "owner_name", "address", "ward", "village", "tehsil", "district", "state", "pincode", "survey_number", "khasra_number", "area_sq_m", "land_use", "property_type", "latitude", "longitude", "geometry", "created_at", "updated_at", "data_type"],
    "property_owners.csv": ["property_id", "person_id", "ownership_type", "ownership_percentage", "data_type"],
    "revenue_records.csv": ["source_record_id", "property_id", "parcel_id", "owner_name", "survey_number", "khasra_number", "area_sq_m", "land_use", "village", "tehsil", "district", "record_status", "dataset_version", "created_at", "updated_at", "data_type"],
    "registration_records.csv": ["registration_id", "property_id", "registration_number", "registered_owner", "registration_date", "transaction_type", "consideration_value", "document_status", "parcel_id", "survey_number", "area_sq_m", "source_department", "data_type"],
    "municipal_records.csv": ["municipal_record_id", "property_id", "property_number", "owner_name", "ward", "address", "property_type", "land_use", "built_up_area_sq_m", "plot_area_sq_m", "property_status", "tax_zone", "data_type"],
    "property_tax_records.csv": ["tax_record_id", "property_id", "assessment_number", "owner_name", "assessed_area_sq_m", "annual_tax", "tax_status", "financial_year", "property_category", "data_type"],
    "gis_records.csv": ["gis_record_id", "property_id", "parcel_id", "geometry", "gis_area_sq_m", "latitude", "longitude", "crs", "boundary_source", "spatial_comparison", "data_type"],
    "planning_records.csv": ["planning_record_id", "property_id", "zoning", "permitted_land_use", "development_status", "planning_zone", "building_permission", "floor_area_ratio", "source_department", "data_type"],
    "satellite_observations.csv": ["observation_id", "property_id", "parcel_id", "image_date", "provider", "cloud_cover", "land_cover", "built_up_percentage", "vegetation_percentage", "water_percentage", "change_detected", "change_confidence", "analysis_status", "analysis_summary", "data_type"],
    "ai_matches.csv": ["match_id", "property_id", "match_score", "match_probability", "confidence_level", "matching_factors", "explanation", "match_status", "data_type"],
    "conflicts.csv": ["conflict_id", "property_id", "parcel_id", "conflict_type", "severity", "description", "status", "created_at", "data_type"],
    "verification_records.csv": ["verification_id", "property_id", "conflict_id", "verification_status", "officer_id", "department", "verification_reason", "verified_at", "data_type"],
    "audit_logs.csv": ["audit_id", "user_id", "role", "department", "action", "record_id", "old_value", "new_value", "reason", "timestamp", "data_type"],
}


def polygon(lon: float, lat: float, size: float = 0.00065) -> dict:
    return {"type": "Polygon", "coordinates": [[[round(lon, 6), round(lat, 6)], [round(lon + size, 6), round(lat, 6)], [round(lon + size, 6), round(lat + size, 6)], [round(lon, 6), round(lat + size, 6)], [round(lon, 6), round(lat, 6)]]]}


def write_csv(name: str, rows: list[dict]) -> None:
    path = DATA_DIR / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS[name])
        writer.writeheader()
        writer.writerows(rows)


def generate() -> dict[str, int]:
    rng = random.Random(SEED)
    DATA_DIR.mkdir(exist_ok=True)
    now = datetime(2026, 9, 10, 12, 0, 0)
    persons: list[dict] = []
    for index in range(1, 201):
        name = NAMES[(index - 1) % len(NAMES)] + (f" {((index - 1) // len(NAMES)) + 1}" if index > len(NAMES) else "")
        persons.append({"person_id": f"PERSON-{index:03d}", "full_name": name, "phone": f"9000000{index:03d}", "email": f"person{index:03d}@example.test", "address": f"Synthetic Block {index % 20 + 1}, Vidisha Urban", "village": VILLAGES[index % len(VILLAGES)], "ward": index % 12 + 1, "tehsil": "Vidisha", "district": "Vidisha", "state": "Madhya Pradesh", "pincode": f"4640{index % 100:02d}", "data_type": DISCLAIMER})
    properties: list[dict] = []
    owners: list[dict] = []
    revenue: list[dict] = []
    registration: list[dict] = []
    municipal: list[dict] = []
    tax: list[dict] = []
    gis: list[dict] = []
    planning: list[dict] = []
    satellite: list[dict] = []
    matches: list[dict] = []
    conflicts: list[dict] = []
    verification: list[dict] = []
    audits: list[dict] = []
    for offset in range(1000):
        number = 1001 + offset
        property_id = f"P{number}"
        person = persons[offset % 200]
        owner = person["full_name"]
        ward = offset % 12 + 1
        lat = 23.505 + (offset % 40) * 0.00115
        lon = 77.775 + (offset // 40) * 0.00125
        area = round(90 + ((offset * 47) % 1450) + rng.random(), 2)
        land_use = LAND_USES[offset % len(LAND_USES)]
        geometry = polygon(lon, lat)
        created = (now - timedelta(days=offset % 700)).isoformat()
        quality = "HIGH" if offset < 700 else "MEDIUM" if offset < 900 else "LOW"
        properties.append({"property_id": property_id, "parcel_id": property_id, "person_id": person["person_id"], "owner_name": owner, "address": f"Sector {offset % 25 + 1}, {person['village']}, Vidisha", "ward": ward, "village": person["village"], "tehsil": "Vidisha", "district": "Vidisha", "state": "Madhya Pradesh", "pincode": person["pincode"], "survey_number": f"SUR-{20000 + offset}", "khasra_number": f"KHA-{50000 + offset}", "area_sq_m": area, "land_use": land_use, "property_type": "Urban Parcel", "latitude": round(lat, 6), "longitude": round(lon, 6), "geometry": json.dumps(geometry, separators=(",", ":")), "created_at": created, "updated_at": now.isoformat(), "data_type": DISCLAIMER})
        owners.append({"property_id": property_id, "person_id": person["person_id"], "ownership_type": "PRIMARY_OWNER", "ownership_percentage": 100, "data_type": DISCLAIMER})
        revenue.append({"source_record_id": f"REV-{number}", "property_id": property_id, "parcel_id": property_id, "owner_name": owner if offset % 9 else owner.replace(" ", " K ", 1), "survey_number": f"SUR-{20000 + offset}", "khasra_number": f"KHA-{50000 + offset}", "area_sq_m": area, "land_use": land_use, "village": person["village"], "tehsil": "Vidisha", "district": "Vidisha", "record_status": "CURRENT", "dataset_version": "v1.0", "created_at": created, "updated_at": now.isoformat(), "data_type": DISCLAIMER})
        if offset < 950: registration.append({"registration_id": f"REG-{number}", "property_id": property_id, "registration_number": f"REGDOC-{number}", "registered_owner": owner, "registration_date": (now - timedelta(days=offset % 1800)).date().isoformat(), "transaction_type": TRANSACTIONS[offset % len(TRANSACTIONS)], "consideration_value": round(area * 12500, 2), "document_status": "ACTIVE", "parcel_id": property_id, "survey_number": f"SUR-{20000 + offset}", "area_sq_m": area, "source_department": "Registration", "data_type": DISCLAIMER})
        if offset < 980: municipal.append({"municipal_record_id": f"MUN-{number}", "property_id": property_id, "property_number": f"MUNPROP-{number}", "owner_name": owner if offset % 11 else owner.replace(" ", " Kumar ", 1), "ward": ward, "address": f"Sector {offset % 25 + 1}, {person['village']}, Vidisha", "property_type": "Urban Parcel", "land_use": land_use if offset % 17 else "Commercial", "built_up_area_sq_m": round(area * .62, 2), "plot_area_sq_m": area, "property_status": "ACTIVE", "tax_zone": f"ZONE-{offset % 5 + 1}", "data_type": DISCLAIMER})
        if offset < 940: tax.append({"tax_record_id": f"TAX-{number}", "property_id": property_id, "assessment_number": f"ASSESS-{number}", "owner_name": owner, "assessed_area_sq_m": area, "annual_tax": round(area * 4.3, 2), "tax_status": TAX_STATUSES[offset % len(TAX_STATUSES)], "financial_year": "2025-26", "property_category": land_use, "data_type": DISCLAIMER})
        comparison = "MATCH" if offset < 700 else "MINOR_VARIANCE" if offset < 900 else "MAJOR_VARIANCE"
        gis.append({"gis_record_id": f"GIS-{number}", "property_id": property_id, "parcel_id": property_id, "geometry": json.dumps(polygon(lon + (.00008 if comparison != 'MATCH' else 0), lat), separators=(",", ":")), "gis_area_sq_m": round(area * (1 if comparison == "MATCH" else 1.02 if comparison == "MINOR_VARIANCE" else 1.12), 2), "latitude": round(lat, 6), "longitude": round(lon, 6), "crs": "EPSG:4326", "boundary_source": "Synthetic GIS survey", "spatial_comparison": comparison, "data_type": DISCLAIMER})
        if offset < 900: planning.append({"planning_record_id": f"PLN-{number}", "property_id": property_id, "zoning": f"Zone {chr(65 + offset % 4)}", "permitted_land_use": land_use if offset % 19 else "Commercial", "development_status": "PERMITTED" if offset % 3 else "UNDER_REVIEW", "planning_zone": f"PLN-{offset % 6 + 1}", "building_permission": "APPROVED" if offset % 4 else "PENDING", "floor_area_ratio": round(1.2 + (offset % 12) / 10, 2), "source_department": "Planning", "data_type": DISCLAIMER})
        if offset < 800:
            built = round(35 + (offset * 13) % 55, 1)
            satellite.append({"observation_id": f"SAT-{number}", "property_id": property_id, "parcel_id": property_id, "image_date": "2026-08-15", "provider": "Synthetic imagery simulator", "cloud_cover": round((offset * 3) % 35, 1), "land_cover": "Built-up / Open", "built_up_percentage": built, "vegetation_percentage": round(100 - built - 8, 1), "water_percentage": 8.0, "change_detected": "true" if offset % 6 == 0 else "false", "change_confidence": round(.75 + (offset % 20) / 100, 2), "analysis_status": "SYNTHETIC_ANALYSIS", "analysis_summary": "Synthetic observation only; no real imagery or legal conclusion.", "data_type": DISCLAIMER})
        factors = {"owner_similarity": .96 if offset % 9 else .84, "parcel_similarity": 1.0, "survey_similarity": 1.0, "area_similarity": .98 if quality == "HIGH" else .91, "address_similarity": .91, "landuse_similarity": .95 if offset % 17 else .62, "gis_similarity": .95 if comparison == "MATCH" else .78}
        score = round(sum(factors.values()) / len(factors), 3)
        matches.append({"match_id": f"MATCH-{number}", "property_id": property_id, "match_score": score, "match_probability": score, "confidence_level": quality, "matching_factors": json.dumps(factors, separators=(",", ":")), "explanation": "Likely candidate match based on parcel, survey, owner similarity and spatial comparison; not a legal ownership decision.", "match_status": "MATCH" if quality == "HIGH" else "POSSIBLE_MATCH" if quality == "MEDIUM" else "REQUIRES_REVIEW", "data_type": DISCLAIMER})
        if offset >= 900 or offset % 10 == 0:
            conflict_type = CONFLICT_TYPES[offset % len(CONFLICT_TYPES)]
            conflict_id = f"CON-{number}"
            conflicts.append({"conflict_id": conflict_id, "property_id": property_id, "parcel_id": property_id, "conflict_type": conflict_type, "severity": "HIGH" if offset >= 990 else "MEDIUM", "description": "Synthetic cross-source inconsistency requiring departmental review; not a legal conclusion.", "status": "OPEN", "created_at": created, "data_type": DISCLAIMER})
        conflict_id = conflicts[-1]["conflict_id"] if conflicts and conflicts[-1]["property_id"] == property_id else ""
        verification.append({"verification_id": f"VER-{number}", "property_id": property_id, "conflict_id": conflict_id, "verification_status": "VERIFIED" if quality == "HIGH" else "REQUIRES_REVIEW" if quality == "LOW" else "AI_MATCHED", "officer_id": f"OFFICER-{offset % 12 + 1:03d}", "department": "Synthetic District Administration", "verification_reason": "Departmental demo verification only; not legally verified ownership.", "verified_at": (now - timedelta(days=offset % 60)).isoformat(), "data_type": DISCLAIMER})
        if offset < 300: audits.append({"audit_id": f"AUD-{offset + 1:04d}", "user_id": f"OFFICER-{offset % 12 + 1:03d}", "role": "DISTRICT_ADMIN", "department": "Synthetic District Administration", "action": ["CREATE", "MATCH", "FLAG", "VERIFY", "UPDATE"][offset % 5], "record_id": property_id, "old_value": "", "new_value": "Synthetic harmonized record", "reason": "Reproducible synthetic audit event.", "timestamp": (now - timedelta(days=offset % 120)).isoformat(), "data_type": DISCLAIMER})
    datasets = {"persons.csv": persons, "properties.csv": properties, "property_owners.csv": owners, "revenue_records.csv": revenue, "registration_records.csv": registration, "municipal_records.csv": municipal, "property_tax_records.csv": tax, "gis_records.csv": gis, "planning_records.csv": planning, "satellite_observations.csv": satellite, "ai_matches.csv": matches, "conflicts.csv": conflicts, "verification_records.csv": verification, "audit_logs.csv": audits}
    for name, rows in datasets.items(): write_csv(name, rows)
    return {name: len(rows) for name, rows in datasets.items()}


if __name__ == "__main__":
    print(json.dumps(generate(), indent=2))
