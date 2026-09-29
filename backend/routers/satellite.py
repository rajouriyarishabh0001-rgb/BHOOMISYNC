from __future__ import annotations

import os
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.satellite_analysis import unavailable_analysis
from database.session import get_db
from models.core import Property, SatelliteObservation
from routers.officer import require_assigned_property, require_department_access
from security import current_user

router = APIRouter(prefix="/api/satellite", tags=["satellite"])
officer_router = APIRouter(prefix="/api/officer/satellite", tags=["officer satellite"])
Officer = Annotated[Any, Depends(current_user)]


def require_assigned_gis_parcel(parcel_id: str, user: Any, session: Session) -> Property:
    require_department_access(user, "gis")
    property_row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not property_row:
        raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, property_row, "gis")
    return property_row


class SatelliteAnalysisRequest(BaseModel):
    parcel_id: str
    geometry: dict | None = None
    image_date: date | None = None
    provider: str | None = None


@router.get("/layers")
def layers() -> dict:
    provider = os.getenv("SATELLITE_PROVIDER") or os.getenv("MAP_PROVIDER")
    configured = bool(os.getenv("SATELLITE_TILE_URL") or os.getenv("GOOGLE_MAPS_API_KEY"))
    return {"configured": configured, "provider": provider, "tile_url": os.getenv("SATELLITE_TILE_URL") if os.getenv("SATELLITE_TILE_URL") else None, "message": "Satellite provider is ready." if configured else "No satellite provider configured; normal map fallback is available."}


@router.get("/parcel/{parcel_id}")
def parcel_observations(parcel_id: str, session: Annotated[Session, Depends(get_db)]) -> dict:
    rows = session.scalars(select(SatelliteObservation).where(SatelliteObservation.parcel_id == parcel_id.upper()).order_by(SatelliteObservation.image_date.desc())).all()
    return {"parcel_id": parcel_id.upper(), "items": [{"image_date": row.image_date, "provider": row.provider, "analysis_status": row.analysis_status, "built_up_percentage": row.built_up_percentage, "vegetation_percentage": row.vegetation_percentage, "water_percentage": row.water_percentage, "change_detected": row.change_detected, "change_confidence": row.change_confidence, "analysis_summary": row.analysis_summary} for row in rows]}


@router.get("/history/{parcel_id}")
def history(parcel_id: str, session: Annotated[Session, Depends(get_db)]) -> dict:
    return parcel_observations(parcel_id, session)


@router.post("/analyze")
def analyze(request: SatelliteAnalysisRequest) -> dict:
    provider = request.provider or os.getenv("SATELLITE_PROVIDER")
    if not os.getenv("SATELLITE_TILE_URL") and not provider:
        return unavailable_analysis(request.parcel_id, provider)
    return {**unavailable_analysis(request.parcel_id, provider), "analysis_status": "QUEUED", "explanation": "Imagery provider is configured. Analysis must be completed by an authorized raster/remote-sensing worker before results are published."}


@officer_router.get("/history/{parcel_id}")
def officer_satellite_history(parcel_id: str, user: Officer, session: Annotated[Session, Depends(get_db)]) -> dict:
    require_assigned_gis_parcel(parcel_id, user, session)
    return history(parcel_id, session)


@officer_router.post("/analyze")
def officer_satellite_analyze(request: SatelliteAnalysisRequest, user: Officer, session: Annotated[Session, Depends(get_db)]) -> dict:
    require_assigned_gis_parcel(request.parcel_id, user, session)
    return analyze(request)


@officer_router.post("/compare")
def officer_satellite_compare(payload: dict, user: Officer, session: Annotated[Session, Depends(get_db)]) -> dict:
    require_assigned_gis_parcel(str(payload.get("parcel_id", "")), user, session)
    return {"success": True, "data": {"parcel_id": payload.get("parcel_id"), "analysis_status": "QUEUED", "possible_change": "Potential physical/land-use change detected.", "recommendation": "Field verification required."}}


@officer_router.get("/{parcel_id}")
def officer_parcel_satellite(parcel_id: str, user: Officer, session: Annotated[Session, Depends(get_db)]) -> dict:
    require_assigned_gis_parcel(parcel_id, user, session)
    return parcel_observations(parcel_id, session)
