"""Public-portal entities; all seeded content is explicitly synthetic."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base

from database.types import GUID


class CitizenTimestamp:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Person(Base, CitizenTimestamp):
    __tablename__ = "persons"
    __table_args__ = (Index("ix_persons_person_id", "person_id"), Index("ix_persons_full_name", "full_name"), Index("ix_persons_name_normalized", "name_normalized"), Index("ix_persons_village", "village"), Index("ix_persons_ward", "ward"))
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    person_id: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(200), nullable=False)
    father_or_guardian_name: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(Text)
    village: Mapped[str | None] = mapped_column(String(120))
    ward: Mapped[int | None] = mapped_column(Integer)
    tehsil: Mapped[str | None] = mapped_column(String(120))
    district: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str | None] = mapped_column(String(120))
    pincode: Mapped[str | None] = mapped_column(String(12))
    data_type: Mapped[str] = mapped_column(String(40), default="SYNTHETIC_DEMO", nullable=False)


class PropertyOwner(Base):
    __tablename__ = "property_owners"
    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)  # public parcel id
    person_id: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    ownership_type: Mapped[str] = mapped_column(String(40), nullable=False)
    ownership_percentage: Mapped[float] = mapped_column(Float, nullable=False)


