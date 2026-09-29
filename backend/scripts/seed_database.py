"""Create normalized SQLAlchemy tables and import the existing local property register."""
from __future__ import annotations

import json
import sqlite3
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

LEGACY_DB = Path(__file__).resolve().parents[1] / "bhoomisync.db"


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


if __name__ == "__main__":
    run()
