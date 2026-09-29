from __future__ import annotations

import json
import math
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import cast, func, select
from geoalchemy2 import Geography
from sqlalchemy.orm import Session, selectinload

from database.session import get_db
from models.core import MapLayer, Parcel, Property
from schemas.map import MapConfigResponse, MapLayerResponse

router = APIRouter(prefix="/api/maps", tags=["maps"])
properties_router = APIRouter(prefix="/api/properties", tags=["property location"])


def layer_response(layer: MapLayer) -> MapLayerResponse:
    return MapLayerResponse(id=str(layer.id), name=layer.name, name_hi=layer.name_hi, layer_type=layer.layer_type, provider=layer.provider, tile_url=layer.tile_url, attribution=layer.attribution, min_zoom=layer.min_zoom, max_zoom=layer.max_zoom)


@router.get("/layers", response_model=list[MapLayerResponse])
def layers(session: Annotated[Session, Depends(get_db)]) -> list[MapLayerResponse]:
    return [layer_response(layer) for layer in session.scalars(select(MapLayer).where(MapLayer.is_active.is_(True)).order_by(MapLayer.layer_type)).all()]


@router.get("/config", response_model=MapConfigResponse)
def config(session: Annotated[Session, Depends(get_db)]) -> MapConfigResponse:
    active = {layer.layer_type: layer_response(layer) for layer in session.scalars(select(MapLayer).where(MapLayer.is_active.is_(True))).all()}
    provider = os.getenv("MAP_PROVIDER", "osm")
    return MapConfigResponse(provider=provider, street=active.get("STREET"), satellite=active.get("SATELLITE"), hybrid=active.get("HYBRID"), satellite_configured=bool(os.getenv("SATELLITE_TILE_URL") or os.getenv("GOOGLE_MAPS_API_KEY")))


@router.get("/parcel/{parcel_id}")
def parcel_map(parcel_id: str, session: Annotated[Session, Depends(get_db)]) -> dict:
    property_row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not property_row:
        raise HTTPException(404, "Property not found")
    parcel = session.scalar(select(Parcel).where(Parcel.parcel_id == parcel_id.upper()).order_by(Parcel.created_at.desc()))
    return {"parcel_id": parcel_id.upper(), "property": {"latitude": property_row.latitude, "longitude": property_row.longitude, "address": property_row.address}, "geometry": parcel.boundary if parcel else None, "centroid": parcel.centroid if parcel else None}


def in_bounds(property_row: Property, north: float, south: float, east: float, west: float) -> bool:
    return bool(property_row.latitude is not None and property_row.longitude is not None and south <= property_row.latitude <= north and west <= property_row.longitude <= east)


@router.get("/viewport")
def viewport(north: float, south: float, east: float, west: float, session: Annotated[Session, Depends(get_db)]) -> dict:
    if north <= south or east <= west:
        raise HTTPException(422, "north must be greater than south and east must be greater than west")
    if session.bind and session.bind.dialect.name == "postgresql":
        envelope = func.ST_MakeEnvelope(west, south, east, north, 4326)
        rows = session.scalars(select(Property).where(func.ST_Within(Property.location, envelope))).all()
        return feature_collection(rows[:500])
    rows = session.scalars(select(Property)).all()
    return feature_collection([row for row in rows if in_bounds(row, north, south, east, west)][:500])


def feature_collection(rows: list[Property]) -> dict:
    features = []
    for row in rows:
        parcel = row.parcels[0] if row.parcels else None
        geometry = parcel.boundary if parcel else ({"type": "Point", "coordinates": [row.longitude, row.latitude]} if row.longitude is not None and row.latitude is not None else None)
        if geometry:
            features.append({"type": "Feature", "geometry": geometry, "properties": {"parcel_id": row.parcel_id, "property_id": row.property_id, "owner_name": row.owner_name, "address": row.address, "area_sq_m": row.area_sq_m, "ward": row.ward, "land_use": row.land_use, "latitude": row.latitude, "longitude": row.longitude, "conflict_status": row.conflict_status, "public_status": "Information may require verification." if row.conflict_status not in (None, "NONE", "CLOSED") else "Information available."}})
    return {"type": "FeatureCollection", "features": features}


@router.get("/nearby")
def nearby(latitude: float, longitude: float, session: Annotated[Session, Depends(get_db)], radius: float = Query(default=1000, gt=0, le=100000)) -> dict:
    if session.bind and session.bind.dialect.name == "postgresql":
        point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
        distance = func.ST_Distance(cast(Property.location, Geography), cast(point, Geography))
        rows = session.execute(select(Property, distance.label("distance")).options(selectinload(Property.parcels)).where(distance <= radius).order_by(distance).limit(500)).all()
        items = [{"parcel_id": row.Property.parcel_id, "owner_name": row.Property.owner_name, "latitude": row.Property.latitude, "longitude": row.Property.longitude, "geometry": row.Property.parcels[0].boundary if row.Property.parcels else None, "distance": round(float(row.distance), 2)} for row in rows]
        return {"items": items, "total": len(items), "radius": radius}
    rows = session.scalars(select(Property).options(selectinload(Property.parcels))).all()
    items = []
    for row in rows:
        if row.latitude is None or row.longitude is None:
            continue
        lat_distance = (row.latitude - latitude) * 111_320
        lon_distance = (row.longitude - longitude) * 111_320 * math.cos(math.radians(latitude))
        distance = math.sqrt(lat_distance**2 + lon_distance**2)
        if distance <= radius:
            items.append({"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude, "geometry": row.parcels[0].boundary if row.parcels else None, "distance": round(distance, 2)})
    return {"items": sorted(items, key=lambda item: item["distance"])[:500], "total": len(items), "radius": radius}


@properties_router.get("/nearby")
def nearby_properties(latitude: float, longitude: float, session: Annotated[Session, Depends(get_db)], radius: float = Query(default=1000, gt=0, le=100000)) -> dict:
    return nearby(latitude=latitude, longitude=longitude, radius=radius, session=session)
