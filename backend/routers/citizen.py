"""Read-only, public-safe citizen portal endpoints."""
from __future__ import annotations

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.session import get_db
from models.citizen import Person, PropertyOwner
from models.core import Property

router = APIRouter(prefix="/api", tags=["citizen portal"])


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", value.lower()).strip()


@router.get("/search/suggestions")
def suggestions(session: Annotated[Session, Depends(get_db)], q: str = Query(min_length=1, max_length=100)) -> dict:
    needle = normalized(q)
    people = session.scalars(select(Person)).all()
    ranked = sorted(((fuzz.WRatio(needle, person.name_normalized), person.full_name) for person in people), reverse=True)
    names: list[str] = []
    for score, name in ranked:
        if score >= 55 and name not in names:
            names.append(name)
        if len(names) == 10:
            break
    return {"query": q, "suggestions": names, "disclaimer": "DEMO / SYNTHETIC DATA — NOT OFFICIAL GOVERNMENT RECORDS"}


@router.get("/persons/{person_id}")
def person_details(person_id: str, session: Annotated[Session, Depends(get_db)]) -> dict:
    person = session.scalar(select(Person).where(Person.person_id == person_id.upper()))
    if not person:
        from fastapi import HTTPException
        raise HTTPException(404, "Person not found")
    parcel_ids = session.scalars(select(PropertyOwner.property_id).where(PropertyOwner.person_id == person.person_id)).all()
    properties = session.scalars(select(Property).where(Property.parcel_id.in_(parcel_ids)).order_by(Property.parcel_id)).all() if parcel_ids else []
    return {"person_id": person.person_id, "full_name": person.full_name, "village": person.village, "district": person.district,
            "properties": [{"parcel_id": row.parcel_id, "property_id": row.property_id, "area_sq_m": row.area_sq_m, "land_use": row.land_use} for row in properties],
            "disclaimer": "DEMO / SYNTHETIC DATA — NOT OFFICIAL GOVERNMENT RECORDS"}
