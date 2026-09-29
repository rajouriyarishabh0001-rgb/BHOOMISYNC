"""Idempotently seed the citizen portal with clearly labelled synthetic data."""
from __future__ import annotations

import re

from sqlalchemy import inspect, select, text

from database.base import Base
from database.connection import engine
from database.session import SessionLocal
from models.citizen import Person, PropertyOwner
from models.core import Parcel, Property
from models.sources import GISRecord


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", value.lower()).strip()


def _ensure_property_columns() -> None:
    """`create_all` does not alter an existing local SQLite MVP database."""
    columns = {item["name"] for item in inspect(engine).get_columns("properties")}
    with engine.begin() as connection:
        if "property_id" not in columns:
            connection.execute(text("ALTER TABLE properties ADD COLUMN property_id VARCHAR(60)"))
        if "data_type" not in columns:
            connection.execute(text("ALTER TABLE properties ADD COLUMN data_type VARCHAR(40) DEFAULT 'SYNTHETIC_DEMO' NOT NULL"))
        # SQLite permits these indexes; PostgreSQL gets the same safe indexes.
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_properties_property_id ON properties (property_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_properties_ward ON properties (ward)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_properties_village ON properties (village)"))


def _ensure_gis_columns() -> None:
    columns = {item["name"] for item in inspect(engine).get_columns("gis_records")}
    additions = {
        "parcel_id": "VARCHAR(60)",
        "latitude": "FLOAT",
        "longitude": "FLOAT",
        "data_type": "VARCHAR(40) DEFAULT 'SYNTHETIC_DEMO' NOT NULL",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(f"ALTER TABLE gis_records ADD COLUMN {name} {definition}"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_gis_records_parcel_id ON gis_records (parcel_id)"))


def run() -> dict[str, int]:
    Base.metadata.create_all(bind=engine)
    _ensure_property_columns()
    _ensure_gis_columns()
    session = SessionLocal()
    try:
        properties = session.scalars(select(Property).order_by(Property.parcel_id)).all()
        for row in properties:
            row.property_id = row.property_id or f"PROP{row.parcel_id.removeprefix('P')}"
            row.data_type = "SYNTHETIC_DEMO"
        session.flush()

        owner_names = list(dict.fromkeys(row.owner_name for row in properties if row.owner_name))
        names = owner_names[:100]
        names.extend([f"Demo Citizen {index:03d}" for index in range(101, 201)])
        people_by_name = {person.full_name: person for person in session.scalars(select(Person)).all()}
        for index, name in enumerate(names, start=1):
            if name in people_by_name:
                continue
            template = next((row for row in properties if row.owner_name == name), None)
            session.add(Person(
                person_id=f"PERSON-{index:03d}", full_name=name, name_normalized=normalize(name),
                father_or_guardian_name="Synthetic guardian record", address=template.address if template else "Synthetic demo address",
                village=template.village if template else "Vidisha Urban", ward=template.ward if template else (index % 12) + 1,
                tehsil=template.tehsil if template else "Vidisha", district=template.district if template else "Vidisha",
                state="Madhya Pradesh", pincode=template.pincode if template else "464001", data_type="SYNTHETIC_DEMO",
            ))
        session.flush()
        people_by_name = {person.full_name: person for person in session.scalars(select(Person)).all()}

        existing_owner_parcels = set(session.scalars(select(PropertyOwner.property_id)).all())
        existing_gis = set(session.scalars(select(GISRecord.parcel_id)).all())
        parcels = {item.parcel_id: item for item in session.scalars(select(Parcel)).all()}
        for row in properties:
            person = people_by_name.get(row.owner_name)
            if person and row.parcel_id not in existing_owner_parcels:
                session.add(PropertyOwner(property_id=row.parcel_id, person_id=person.person_id, ownership_type="PRIMARY_OWNER", ownership_percentage=100))
            if row.parcel_id not in existing_gis:
                parcel = parcels.get(row.parcel_id)
                session.add(GISRecord(parcel_id=row.parcel_id, latitude=row.latitude, longitude=row.longitude,
                    geometry=parcel.boundary if parcel else None, source_department="DEMO_GIS",
                    source_record_id=row.parcel_id, data_type="SYNTHETIC_DEMO"))
        session.commit()
        return {"persons": session.query(Person).count(), "properties": len(properties), "gis_records": session.query(GISRecord).count()}
    finally:
        session.close()


if __name__ == "__main__":
    print(run())
