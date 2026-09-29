from typing import Any

from pydantic import BaseModel, Field


class PropertySearchRequest(BaseModel):
    query: str = ""
    parcel_id: str | None = None
    survey_number: str | None = None
    khasra_number: str | None = None
    owner_name: str | None = None
    address: str | None = None
    district: str | None = None
    city: str | None = None
    village: str | None = None
    ward: int | None = None
    minimum_area: float | None = Field(default=None, ge=0)
    maximum_area: float | None = Field(default=None, ge=0)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class PropertyResponse(BaseModel):
    parcel_id: str
    owner_name: str
    area_sq_m: float | None
    area_sq_ft: float | None
    land_use: str | None
    address: str | None
    ward: int | None
    district: str | None
    state: str | None
    latitude: float | None
    longitude: float | None
    verification_status: str | None
    conflict_status: str | None
    geojson: dict[str, Any] | None = None
