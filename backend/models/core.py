from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from database.base import Base
from database.geometry import PortableGeometry
from database.types import GUID


def uuid_column() -> Mapped[uuid.UUID]:
    return mapped_column(GUID(), primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = uuid_column()
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_email", "email"),)
    id: Mapped[uuid.UUID] = uuid_column()
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))
    designation: Mapped[str | None] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    role: Mapped[Role] = relationship(back_populates="users")
    locations: Mapped[list["UserLocation"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Property(Base, TimestampMixin):
    __tablename__ = "properties"
    __table_args__ = (Index("ix_properties_parcel_id", "parcel_id"), Index("ix_properties_property_id", "property_id"), Index("ix_properties_owner_name", "owner_name"), Index("ix_properties_survey_number", "survey_number"), Index("ix_properties_khasra_number", "khasra_number"), Index("ix_properties_ward", "ward"), Index("ix_properties_village", "village"))
    id: Mapped[uuid.UUID] = uuid_column()
    parcel_id: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    # Public, stable display identifier.  It is intentionally distinct from the
    # internal UUID primary key used by officer workflows.
    property_id: Mapped[str | None] = mapped_column(String(60), unique=True)
    survey_number: Mapped[str | None] = mapped_column(String(80))
    khasra_number: Mapped[str | None] = mapped_column(String(80))
    owner_name: Mapped[str] = mapped_column(String(200), nullable=False)
    co_owner_name: Mapped[str | None] = mapped_column(String(200))
    father_or_guardian_name: Mapped[str | None] = mapped_column(String(200))
    property_type: Mapped[str | None] = mapped_column(String(100))
    land_use: Mapped[str | None] = mapped_column(String(100))
    area_sq_m: Mapped[float | None] = mapped_column(Float)
    area_sq_ft: Mapped[float | None] = mapped_column(Float)
    address: Mapped[str | None] = mapped_column(Text)
    ward: Mapped[int | None] = mapped_column(Integer)
    zone: Mapped[str | None] = mapped_column(String(100))
    village: Mapped[str | None] = mapped_column(String(120))
    tehsil: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    pincode: Mapped[str | None] = mapped_column(String(12))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    property_status: Mapped[str | None] = mapped_column(String(60))
    verification_status: Mapped[str | None] = mapped_column(String(60))
    conflict_status: Mapped[str | None] = mapped_column(String(60))
    data_type: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_DEMO", nullable=False)
    location: Mapped[dict[str, Any] | None] = mapped_column(PortableGeometry("POINT", 4326))
    parcels: Mapped[list["Parcel"]] = relationship(back_populates="property", cascade="all, delete-orphan")
    conflicts: Mapped[list["Conflict"]] = relationship(back_populates="property", cascade="all, delete-orphan")


class Parcel(Base, TimestampMixin):
    __tablename__ = "parcels"
    __table_args__ = (Index("ix_parcels_parcel_id", "parcel_id"),)
    id: Mapped[uuid.UUID] = uuid_column()
    parcel_id: Mapped[str] = mapped_column(String(60), nullable=False)
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), nullable=False)
    survey_number: Mapped[str | None] = mapped_column(String(80))
    khasra_number: Mapped[str | None] = mapped_column(String(80))
    boundary: Mapped[dict[str, Any] | None] = mapped_column(PortableGeometry("MULTIPOLYGON", 4326))
    centroid: Mapped[dict[str, Any] | None] = mapped_column(PortableGeometry("POINT", 4326))
    calculated_area: Mapped[float | None] = mapped_column(Float)
    authoritative_area: Mapped[float | None] = mapped_column(Float)
    crs: Mapped[str] = mapped_column(String(30), default="EPSG:4326")
    geometry_source: Mapped[str | None] = mapped_column(String(100))
    geometry_version: Mapped[str | None] = mapped_column(String(30))
    property: Mapped[Property] = relationship(back_populates="parcels")


class MapLayer(Base, TimestampMixin):
    __tablename__ = "map_layers"
    id: Mapped[uuid.UUID] = uuid_column()
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    name_hi: Mapped[str | None] = mapped_column(String(160))
    layer_type: Mapped[str] = mapped_column(String(40), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    tile_url: Mapped[str | None] = mapped_column(Text)
    attribution: Mapped[str | None] = mapped_column(Text)
    min_zoom: Mapped[int] = mapped_column(Integer, default=0)
    max_zoom: Mapped[int] = mapped_column(Integer, default=22)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserLocation(Base, TimestampMixin):
    __tablename__ = "user_locations"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    accuracy: Mapped[float | None] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    user: Mapped[User] = relationship(back_populates="locations")


class SatelliteObservation(Base, TimestampMixin):
    __tablename__ = "satellite_observations"
    id: Mapped[uuid.UUID] = uuid_column()
    parcel_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    image_date: Mapped[date | None] = mapped_column(Date)
    provider: Mapped[str | None] = mapped_column(String(80))
    image_url: Mapped[str | None] = mapped_column(Text)
    tile_url: Mapped[str | None] = mapped_column(Text)
    geometry: Mapped[dict[str, Any] | None] = mapped_column(PortableGeometry("POLYGON", 4326))
    resolution: Mapped[float | None] = mapped_column(Float)
    cloud_cover: Mapped[float | None] = mapped_column(Float)
    analysis_status: Mapped[str | None] = mapped_column(String(40))
    land_cover: Mapped[str | None] = mapped_column(String(100))
    built_up_percentage: Mapped[float | None] = mapped_column(Float)
    vegetation_percentage: Mapped[float | None] = mapped_column(Float)
    water_percentage: Mapped[float | None] = mapped_column(Float)
    change_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    change_confidence: Mapped[float | None] = mapped_column(Float)
    analysis_summary: Mapped[str | None] = mapped_column(Text)


class Conflict(Base, TimestampMixin):
    __tablename__ = "conflicts"
    id: Mapped[uuid.UUID] = uuid_column()
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), nullable=False)
    conflict_type: Mapped[str] = mapped_column(String(50), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_a: Mapped[str | None] = mapped_column(String(100))
    source_b: Mapped[str | None] = mapped_column(String(100))
    detected_by: Mapped[str | None] = mapped_column(String(100))
    match_score: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    resolution: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    property: Mapped[Property] = relationship(back_populates="conflicts")


class SourceRecord(Base, TimestampMixin):
    __tablename__ = "source_records"
    id: Mapped[uuid.UUID] = uuid_column()
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"))
    source_department: Mapped[str] = mapped_column(String(100), nullable=False)
    source_record_id: Mapped[str] = mapped_column(String(100), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(100))
    dataset_version: Mapped[str | None] = mapped_column(String(50))
    original_values: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[uuid.UUID] = uuid_column()
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str | None] = mapped_column(String(50))
    department: Mapped[str | None] = mapped_column(String(100))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class VerificationRecord(Base, TimestampMixin):
    __tablename__ = "verification_records"
    id: Mapped[uuid.UUID] = uuid_column()
    property_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("properties.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    department: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(Text)


class RecordVersion(Base):
    __tablename__ = "record_versions"
    id: Mapped[uuid.UUID] = uuid_column()
    property_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("properties.id"))
    source_record_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("source_records.id"))
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    department: Mapped[str | None] = mapped_column(String(100))
    reason: Mapped[str | None] = mapped_column(Text)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
