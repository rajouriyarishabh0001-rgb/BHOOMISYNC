"""Create normalized SQLAlchemy tables and import the existing local property register."""
from __future__ import annotations

import json
import sqlite3
import csv
from datetime import date
from pathlib import Path

from sqlalchemy import select
from shapely.geometry import MultiPolygon, shape, mapping

from database.base import Base
from database.connection import engine
from database.session import SessionLocal
from models.core import Conflict, Parcel, Property, SourceRecord
from models.officer import SourceDataset
from models.core import SatelliteObservation
from models.sources import ElectricityRecord, MunicipalRecord, PlanningRecord, PropertyTaxRecord, RegistrationRecord, RevenueRecord

LEGACY_DB = Path(__file__).resolve().parents[1] / "bhoomisync.db"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def run() -> None:
    Base.metadata.create_all(bind=engine)
    if not LEGACY_DB.exists():
        print("Normalized tables created; no legacy property database found.")
        return

    legacy = sqlite3.connect(LEGACY_DB)
    legacy.row_factory = sqlite3.Row
    rows = legacy.execute("SELECT * FROM properties ORDER BY parcel_id").fetchall()
    gis_rows = {row["parcel_id"]: row for row in legacy.execute("SELECT * FROM gis_parcels").fetchall()}
    dataset_rows = legacy.execute("SELECT * FROM source_datasets").fetchall()
    conflict_rows = legacy.execute("SELECT * FROM conflicts").fetchall()
    satellite_rows = legacy.execute("SELECT * FROM satellite_observations").fetchall()
    session = SessionLocal()
    imported = 0
    try:
        existing_datasets = {value for value in session.scalars(select(SourceDataset.dataset_name)).all()}
        for row in dataset_rows:
            if row["dataset_name"] not in existing_datasets:
                session.add(SourceDataset(dataset_name=row["dataset_name"], department=row["department"], source_type="LEGACY_IMPORT", record_count=row["record_count"], dataset_version=row["version"], processing_status="COMPLETED", harmonization_status="COMPLETED"))
        session.flush()
        existing = set(session.scalars(select(Property.parcel_id)).all())
        for row in rows:
            if row["parcel_id"] in existing:
                continue
            point = {"type": "Point", "coordinates": [row["longitude"], row["latitude"]]}
            property_row = Property(
                parcel_id=row["parcel_id"], survey_number=row["survey_number"], khasra_number=row["khasra_number"],
                owner_name=row["owner_name"], co_owner_name=row["co_owner_name"], area_sq_m=row["area_sq_m"],
                area_sq_ft=row["area_sq_ft"], land_use=row["land_use"], property_type=row["property_type"],
                address=row["address"], ward=row["ward"], zone=row["zone"], village=row["village"],
                tehsil=row["tehsil"], district=row["district"], state=row["state"], pincode=row["pincode"],
                latitude=row["latitude"], longitude=row["longitude"], property_status=row["property_status"],
                verification_status=row["verification_status"], conflict_status=row["conflict_status"], location=point,
            )
            session.add(property_row)
            session.flush()
            gis = gis_rows.get(row["parcel_id"])
            if gis:
                boundary = json.loads(gis["geometry"])
                boundary_shape = shape(boundary)
                if boundary_shape.geom_type == "Polygon":
                    boundary = mapping(MultiPolygon([boundary_shape]))
                session.add(Parcel(
                    parcel_id=row["parcel_id"], property_id=property_row.id, survey_number=row["survey_number"],
                    khasra_number=row["khasra_number"], boundary=boundary,
                    centroid={"type": "Point", "coordinates": [row["longitude"] + .0005, row["latitude"] + .0005]},
                    calculated_area=gis["gis_area_sq_m"], authoritative_area=row["area_sq_m"], crs=gis["crs"],
                    geometry_source="legacy GIS import", geometry_version="v1",
                ))
            session.add(SourceRecord(
                property_id=property_row.id, source_department="HARMONIZED_IMPORT",
                source_record_id=row["parcel_id"], dataset_id="legacy-bhoomisync", dataset_version="v1",
                original_values={"owner_name": row["owner_name"], "area_sq_m": row["area_sq_m"], "land_use": row["land_use"]},
            ))
            imported += 1
        for row in satellite_rows:
            session.add(SatelliteObservation(parcel_id=row["parcel_id"], image_date=date.fromisoformat(row["image_date"]) if row["image_date"] else None, provider=row["provider"], tile_url=row["tile_url"], analysis_status=row["analysis_status"], land_cover=row["land_cover"], built_up_percentage=row["built_up_percentage"], vegetation_percentage=row["vegetation_percentage"], water_percentage=row["water_percentage"], change_detected=bool(row["change_detected"]), change_confidence=row["change_confidence"], analysis_summary=row["analysis_summary"]))
        property_ids = {value: value for value in session.scalars(select(Property.parcel_id)).all()}
        existing_conflicts = {value for value in session.scalars(select(Conflict.description)).all()}
        for row in conflict_rows:
            if row["description"] in existing_conflicts or row["parcel_id"] not in property_ids:
                continue
            property_row = session.scalar(select(Property).where(Property.parcel_id == row["parcel_id"]))
            session.add(Conflict(property_id=property_row.id, conflict_type=row["conflict_type"], severity=row["severity"], description=row["description"], status=row["status"], detected_by=row["source_department"]))
        session.commit()
    finally:
        session.close()
        legacy.close()
    print(f"Normalized database ready: imported {imported} properties from {LEGACY_DB}")


def seed_departmental_records() -> dict[str, int]:
    """Idempotently load synthetic department CSVs into normalized source tables."""
    session = SessionLocal()
    imported = {"municipal": 0, "registration": 0, "revenue": 0, "property_tax": 0, "planning": 0, "electricity": 0}
    try:
        properties = {row.parcel_id: row for row in session.scalars(select(Property)).all()}
        specs = [
            ("municipal_records.csv", MunicipalRecord, "municipal_record_id", lambda row, prop: {"owner_name": row.get("owner_name"), "address": row.get("address"), "ward": _int_value(row.get("ward")), "zone": row.get("tax_zone"), "land_use": row.get("land_use"), "plot_area": _float_value(row.get("plot_area_sq_m"))}),
            ("registration_records.csv", RegistrationRecord, "registration_id", lambda row, prop: {"document_number": row.get("registration_number"), "party_names": {"registered_owner": row.get("registered_owner"), "transaction_type": row.get("transaction_type"), "consideration_value": row.get("consideration_value"), "document_status": row.get("document_status")}, "registration_date": row.get("registration_date"), "property_type": row.get("transaction_type"), "area_original": _float_value(row.get("area_sq_m"))}),
            ("revenue_records.csv", RevenueRecord, "source_record_id", lambda row, prop: {"owner_name": row.get("owner_name"), "area_original": _float_value(row.get("area_sq_m")), "area_unit": "sq.m", "land_classification": row.get("land_use"), "mutation_status": row.get("record_status")}),
            ("property_tax_records.csv", PropertyTaxRecord, "tax_record_id", lambda row, prop: {"owner_name": row.get("owner_name"), "assessment_year": _int_value((row.get("financial_year") or "").split("-")[0]), "tax_amount": _float_value(row.get("annual_tax")), "category": row.get("property_category"), "assessed_area": _float_value(row.get("assessed_area_sq_m")), "tax_status": row.get("tax_status"), "address": prop.address}),
            ("planning_records.csv", PlanningRecord, "planning_record_id", lambda row, prop: {"planning_zone": row.get("planning_zone"), "land_use": row.get("permitted_land_use"), "development_zone": row.get("zoning"), "restrictions": f"Building permission: {row.get('building_permission')}; FAR: {row.get('floor_area_ratio')}"}),
        ]
        for filename, model, record_key, values_for in specs:
            path = DATA_DIR / filename
            if not path.exists():
                continue
            existing = set(session.scalars(select(model.source_record_id)).all())
            with path.open("r", encoding="utf-8-sig", newline="") as source:
                for row in csv.DictReader(source):
                    record_id = row.get(record_key) or row.get("source_record_id")
                    property_row = properties.get(row.get("property_id") or row.get("parcel_id") or "")
                    if not record_id or record_id in existing or not property_row:
                        continue
                    session.add(model(property_id=property_row.id, source_department=row.get("source_department") or model.__name__.removesuffix("Record"), source_record_id=record_id, dataset_id=filename, dataset_version=row.get("dataset_version") or "demo-v1", original_values=row, **values_for(row, property_row)))
                    existing.add(record_id)
                    imported[model.__tablename__.removesuffix("_records")] += 1

        existing_electricity = set(session.scalars(select(ElectricityRecord.source_record_id)).all())
        for property_row in properties.values():
            record_id = f"ELEC-{property_row.parcel_id}"
            if record_id in existing_electricity:
                continue
            demo_values = {"consumer_number": f"CON-{property_row.parcel_id}", "owner_name": property_row.owner_name, "meter_number": f"MTR-{property_row.parcel_id}", "connection_status": "ACTIVE", "address": property_row.address, "sanctioned_load_kw": 5.0, "category": property_row.property_type or "RESIDENTIAL", "data_type": "SYNTHETIC_DEMO"}
            session.add(ElectricityRecord(property_id=property_row.id, source_department="Electricity", source_record_id=record_id, dataset_id="synthetic-electricity-demo", dataset_version="demo-v1", original_values=demo_values, **{key: value for key, value in demo_values.items() if key != "data_type"}))
            imported["electricity"] += 1
        session.commit()
        return imported
    finally:
        session.close()


def _float_value(value: str | None) -> float | None:
    try:
        return float(value) if value else None
    except ValueError:
        return None


def _int_value(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


if __name__ == "__main__":
    run()
