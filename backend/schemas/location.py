from uuid import UUID

from pydantic import BaseModel, Field


class LocationCreate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)
    source: str = Field(default="BROWSER", pattern="^(GPS|BROWSER|MANUAL)$")


class LocationResponse(LocationCreate):
    id: UUID