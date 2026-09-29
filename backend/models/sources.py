from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.types import GUID


class SourceRecordFields:
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"), index=True)
    source_department: Mapped[str] = mapped_column(String(100), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    dataset_id: Mapped[str | None] = mapped_column(String(100))
    dataset_version: Mapped[str | None] = mapped_column(String(50))
    original_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class RevenueRecord(SourceRecordFields, Base):
    __tablename__ = "revenue_records"
    owner_name: Mapped[str | None] = mapped_column(String(200))
    area_original: Mapped[float | None] = mapped_column(Float)
    area_unit: Mapped[str | None] = mapped_column(String(30))
    land_classification: Mapped[str | None] = mapped_column(String(100))
    mutation_status: Mapped[str | None] = mapped_column(String(60))


class RegistrationRecord(SourceRecordFields, Base):
    __tablename__ = "registration_records"
    document_number: Mapped[str | None] = mapped_column(String(100))
    party_names: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    registration_date: Mapped[str | None] = mapped_column(String(20))
    property_type: Mapped[str | None] = mapped_column(String(100))
    area_original: Mapped[float | None] = mapped_column(Float)


class MunicipalRecord(SourceRecordFields, Base):
    __tablename__ = "municipal_records"
    owner_name: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    ward: Mapped[int | None] = mapped_column(Integer)
    zone: Mapped[str | None] = mapped_column(String(100))
    land_use: Mapped[str | None] = mapped_column(String(100))
    plot_area: Mapped[float | None] = mapped_column(Float)
    built_up_area: Mapped[float | None] = mapped_column(Float)


class ElectricityRecord(SourceRecordFields, Base):
    __tablename__ = "electricity_records"
    consumer_number: Mapped[str | None] = mapped_column(String(120))
    owner_name: Mapped[str | None] = mapped_column(String(200))
    meter_number: Mapped[str | None] = mapped_column(String(120))
    connection_status: Mapped[str | None] = mapped_column(String(60))
    address: Mapped[str | None] = mapped_column(Text)
    sanctioned_load_kw: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(100))


class PropertyTaxRecord(SourceRecordFields, Base):
    __tablename__ = "property_tax_records"
    owner_name: Mapped[str | None] = mapped_column(String(200))
    assessment_year: Mapped[int | None] = mapped_column(Integer)
    tax_amount: Mapped[float | None] = mapped_column(Float)
    category: Mapped[str | None] = mapped_column(String(100))
    assessed_area: Mapped[float | None] = mapped_column(Float)
    tax_status: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text)


class PlanningRecord(SourceRecordFields, Base):
    __tablename__ = "planning_records"
    planning_zone: Mapped[str | None] = mapped_column(String(100))
    land_use: Mapped[str | None] = mapped_column(String(100))
    development_zone: Mapped[str | None] = mapped_column(String(100))
    restrictions: Mapped[str | None] = mapped_column(Text)


class GISRecord(SourceRecordFields, Base):
    __tablename__ = "gis_records"

    parcel_id: Mapped[str] = mapped_column(
        String(60),
        unique=True,
        nullable=False,
        index=True
    )

    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)

    geometry: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    gis_area_sq_m: Mapped[float | None] = mapped_column(Float)

    crs: Mapped[str | None] = mapped_column(String(30))

    spatial_comparison: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    data_type: Mapped[str] = mapped_column(
        String(40),
        default="SYNTHETIC_DEMO",
        nullable=False
    )