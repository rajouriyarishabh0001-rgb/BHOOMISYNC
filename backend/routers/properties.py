from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from rapidfuzz.fuzz import ratio

from database.session import get_db
from models.core import Parcel, Property
from models.citizen import Person, PropertyOwner
from models.sources import GISRecord
from schemas.property import PropertyResponse, PropertySearchRequest
import re

router = APIRouter(prefix="/api", tags=["normalized properties"])


def property_response(row: Property) -> dict:
    parcel = row.parcels[0] if row.parcels else None
    geometry = parcel.boundary if parcel else None
    public_status = "Information may require verification." if row.conflict_status not in (None, "NONE", "CLOSED") else "Information available."
    return {"parcel_id": row.parcel_id, "property_id": row.property_id, "owner_name": row.owner_name, "survey_number": row.survey_number, "khasra_number": row.khasra_number, "area_sq_m": row.area_sq_m, "land_use": row.land_use, "property_type": row.property_type, "address": row.address, "ward": row.ward, "village": row.village, "tehsil": row.tehsil, "district": row.district, "state": row.state, "pincode": row.pincode, "latitude": row.latitude, "longitude": row.longitude, "location_available": row.latitude is not None and row.longitude is not None, "verification_status": row.verification_status, "public_status": public_status, "geometry": geometry, "geojson": {"type": "Feature", "geometry": geometry, "properties": {"parcel_id": row.parcel_id, "land_use": row.land_use}}, "disclaimer": "DEMO / SYNTHETIC DATA — NOT OFFICIAL GOVERNMENT RECORDS"}


@router.get("/properties")
def normalized_properties(session: Annotated[Session, Depends(get_db)], page: int = 1, page_size: int = 25) -> dict:
    page_size = min(max(page_size, 1), 100)
    rows = session.scalars(select(Property).order_by(Property.parcel_id).offset((page - 1) * page_size).limit(page_size)).all()
    total = session.scalar(select(func.count()).select_from(Property)) or 0
    items = [property_response(row) for row in rows]
    return {"items": items, "results": items, "total": total, "page": page, "page_size": page_size}


@router.get("/properties/{parcel_id}")
def normalized_property(parcel_id: str, session: Annotated[Session, Depends(get_db)]) -> dict:
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row:
        raise HTTPException(404, "Property not found")
    return property_response(row)


@router.post("/search")
def normalized_search(request: PropertySearchRequest, session: Annotated[Session, Depends(get_db)]) -> dict:
    filters = []
    if request.parcel_id: filters.append(Property.parcel_id.ilike(f"%{request.parcel_id}%"))
    if request.survey_number: filters.append(Property.survey_number.ilike(f"%{request.survey_number}%"))
    if request.khasra_number: filters.append(Property.khasra_number.ilike(f"%{request.khasra_number}%"))
    if request.owner_name: filters.append(Property.owner_name.ilike(f"%{request.owner_name}%"))
    if request.address: filters.append(Property.address.ilike(f"%{request.address}%"))
    if request.district or request.city:
        location = request.district or request.city
        filters.append(Property.district.ilike(f"%{location}%"))
    if request.ward is not None: filters.append(Property.ward == request.ward)
    if request.minimum_area is not None: filters.append(Property.area_sq_m >= request.minimum_area)
    if request.maximum_area is not None: filters.append(Property.area_sq_m <= request.maximum_area)
    if request.query:
        query = request.query.strip()
        parcel_match = re.search(r"\bP\d{4,}\b", query.upper())
        city_names = ["bhopal", "indore", "vidisha", "jabalpur", "gwalior", "ujjain", "sagar", "dewas"]
        city = next((name for name in city_names if name in query.lower()), None)
        property_match = re.search(r"\bPROP\d{4,}\b", query.upper())
        survey_match = re.search(r"\b(?:SUR|SV)-?\d+\b", query.upper())
        khasra_match = re.search(r"\b(?:KHA|KH)-?\d+\b", query.upper())
        ward_match = re.search(r"(?:ward|वार्ड)\s*(\d+)", query.lower())
        if parcel_match:
            filters.append(Property.parcel_id == parcel_match.group(0))
        elif property_match:
            filters.append(Property.property_id == property_match.group(0))
        elif survey_match:
            filters.append(Property.survey_number.ilike(f"%{survey_match.group(0)}%"))
        elif khasra_match:
            filters.append(Property.khasra_number.ilike(f"%{khasra_match.group(0)}%"))
        elif ward_match:
            filters.append(Property.ward == int(ward_match.group(1)))
        elif city:
            filters.append(Property.district.ilike(f"%{city}%"))
            owner_query = re.sub(rf"\b(find|show|search|meri|ki|ka|ke|property|properties|zameen|land|in|mein|{city})\b", " ", query, flags=re.IGNORECASE)
            owner_query = re.sub(r"\s+", " ", owner_query).strip()
            if owner_query:
                filters.append(Property.owner_name.ilike(f"%{owner_query}%"))
        else:
            owner_query = re.sub(r"\b(find|show|search|meri|ki|ka|ke|property|properties|zameen|land|in|mein|की|की जमीन)\b", " ", query, flags=re.IGNORECASE).strip()
            filters.append(or_(Property.parcel_id.ilike(f"%{query}%"), Property.owner_name.ilike(f"%{owner_query or query}%"), Property.address.ilike(f"%{owner_query or query}%")))
    candidate_statement = select(Property).where(*filters)
    candidates = session.scalars(candidate_statement).all()
    if request.query and not candidates:
        candidates = session.scalars(select(Property)).all()
    query_text = request.query.strip().lower()
    def score(row: Property) -> float:
        if not query_text:
            return 100.0
        values = [row.owner_name, row.parcel_id, row.property_id, row.survey_number, row.khasra_number, row.address, row.village, row.district]
        return round(max(ratio(query_text, str(value or '').lower()) for value in values), 2)
    ranked = [row for row in sorted(candidates, key=score, reverse=True) if not request.query or score(row) >= 55 or request.ward is not None]
    total = len(ranked)
    items = ranked[(request.page - 1) * request.page_size:request.page * request.page_size]
    results = []
    for row in items:
        owner = session.scalar(select(PropertyOwner).where(PropertyOwner.property_id == row.parcel_id))
        result = {"person_id": owner.person_id if owner else None, "parcel_id": row.parcel_id, "property_id": row.property_id, "owner_name": row.owner_name, "area_sq_m": row.area_sq_m, "land_use": row.land_use, "address": row.address, "ward": row.ward, "village": row.village, "district": row.district, "match_score": score(row)}
        results.append(result)
    return {"query": request.query, "items": results, "results": results, "total": total, "page": request.page, "page_size": request.page_size, "disclaimer": "DEMO / SYNTHETIC DATA — NOT OFFICIAL GOVERNMENT RECORDS"}
