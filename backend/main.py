from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import inspect
from rapidfuzz.fuzz import ratio

from database.base import Base
from database.connection import database_status, engine
from database.session import SessionLocal
from models.core import MapLayer, Property, Role, User
from models.officer import Department, OfficerAssignment, Permission, RolePermission
from models import sources, citizen
from models import officer
from routers.auth import router as auth_router
from routers.location import router as location_router
from routers.maps import router as maps_router
from routers.maps import properties_router as properties_location_router
from routers.properties import router as normalized_properties_router
from routers.ai import router as ai_router
from routers.satellite import router as satellite_router, officer_router as officer_satellite_router
from routers.officer import router as officer_router
from routers.citizen import router as citizen_router
from security import hash_password

from scripts.seed_demo_data import DB_PATH, schema
from scripts.seed_citizen_portal import _ensure_property_columns

app = FastAPI(title="BHOOMISYNC API", version="0.2.0", description="Synthetic urban land harmonization API. Not an official government platform.")
cors_origins = [origin.strip() for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["Content-Type", "Authorization"])
app.include_router(auth_router)
app.include_router(location_router)
app.include_router(maps_router)
app.include_router(properties_location_router)
app.include_router(normalized_properties_router)
app.include_router(ai_router)
app.include_router(satellite_router)
app.include_router(officer_satellite_router)
app.include_router(officer_router)
app.include_router(citizen_router)


@app.on_event("startup")
def initialize_architecture() -> None:
    Base.metadata.create_all(bind=engine)
    if engine.dialect.name == "sqlite" and "designation" not in {column["name"] for column in inspect(engine).get_columns("users")}:
        with engine.begin() as connection:
            connection.exec_driver_sql("ALTER TABLE users ADD COLUMN designation VARCHAR(120)")
    _ensure_property_columns()
    session = SessionLocal()
    try:
        role_names = ["CITIZEN", "REVENUE_OFFICER", "REGISTRATION_OFFICER", "MUNICIPAL_OFFICER", "ELECTRICITY_OFFICER", "PROPERTY_TAX_OFFICER", "GIS_SURVEY_OFFICER", "PLANNING_OFFICER", "DEPARTMENT_ADMIN", "DISTRICT_ADMIN", "SUPER_ADMIN"]
        existing_roles = {role.name for role in session.query(Role).all()}
        for role_name in role_names:
            if role_name not in existing_roles:
                session.add(Role(name=role_name, description=f"BHOOMISYNC {role_name.replace('_', ' ').title()} role"))
        session.flush()
        departments = [("REV", "Revenue", "राजस्व"), ("REG", "Registration", "पंजीयन"), ("MUNICIPAL", "Municipal", "नगरपालिका"), ("ELECTRICITY", "Electricity", "विद्युत"), ("TAX", "Property Tax", "संपत्ति कर"), ("GIS", "GIS Survey", "जीआईएस सर्वेक्षण"), ("PLANNING", "Planning", "नियोजन"), ("ADMIN", "District Administration", "जिला प्रशासन")]
        existing_departments = {item.department_code for item in session.query(Department).all()}
        for code, name, name_hi in departments:
            if code not in existing_departments:
                session.add(Department(department_code=code, department_name=name, department_name_hi=name_hi))
        permission_names = ["PROPERTY_VIEW", "PROPERTY_EDIT", "RECORD_VIEW", "RECORD_UPLOAD", "GIS_VIEW", "GIS_EDIT", "GIS_ANALYZE", "SATELLITE_VIEW", "SATELLITE_ANALYZE", "AI_VIEW", "AI_MATCH", "AI_SCAN", "CONFLICT_VIEW", "CONFLICT_RESOLVE", "VERIFICATION_VIEW", "VERIFICATION_APPROVE", "REPORT_VIEW", "REPORT_EXPORT", "AUDIT_VIEW", "USER_MANAGE", "ROLE_MANAGE"]
        existing_permissions = {item.code for item in session.query(Permission).all()}
        for code in permission_names:
            if code not in existing_permissions:
                session.add(Permission(code=code, description=code.replace("_", " ").title()))
        session.flush()
        all_roles = {role.name: role for role in session.query(Role).all()}
        all_permissions = {item.code: item for item in session.query(Permission).all()}
        existing_pairs = {(item.role_id, item.permission_id) for item in session.query(RolePermission).all()}
        for role_name, role in all_roles.items():
            if role_name in {"SUPER_ADMIN", "DISTRICT_ADMIN"}:
                role_permissions = set(permission_names)
            elif role_name in {"DEPARTMENT_ADMIN"}:
                role_permissions = {"PROPERTY_VIEW", "PROPERTY_EDIT", "RECORD_VIEW", "RECORD_UPLOAD", "CONFLICT_VIEW", "VERIFICATION_VIEW", "VERIFICATION_APPROVE", "REPORT_VIEW", "USER_MANAGE"}
            elif role_name == "GIS_SURVEY_OFFICER":
                role_permissions = {"PROPERTY_VIEW", "RECORD_VIEW", "GIS_VIEW", "GIS_EDIT", "GIS_ANALYZE", "AI_VIEW", "AI_MATCH", "AI_SCAN", "SATELLITE_VIEW", "SATELLITE_ANALYZE", "CONFLICT_VIEW", "VERIFICATION_VIEW", "VERIFICATION_APPROVE"}
            elif role_name.endswith("OFFICER"):
                role_permissions = {"PROPERTY_VIEW", "PROPERTY_EDIT", "RECORD_VIEW", "CONFLICT_VIEW", "VERIFICATION_VIEW", "VERIFICATION_APPROVE"}
            elif role_name == "CITIZEN":
                role_permissions = {"PROPERTY_VIEW"}
            else:
                role_permissions = set()
            if role_name == "DEPARTMENT_ADMIN":
                role_permissions.update({"PROPERTY_EDIT", "RECORD_UPLOAD", "VERIFICATION_APPROVE", "REPORT_VIEW", "USER_MANAGE"})
            for existing in session.query(RolePermission).filter_by(role_id=role.id).all():
                permission_code = next((code for code, permission in all_permissions.items() if permission.id == existing.permission_id), None)
                if permission_code not in role_permissions:
                    session.delete(existing)
            for code in role_permissions:
                pair = (role.id, all_permissions[code].id)
                if pair not in existing_pairs:
                    session.add(RolePermission(role_id=role.id, permission_id=all_permissions[code].id))
        demo_users = [("revenue.demo@bhoomisync.local", "Revenue Officer", "REVENUE_OFFICER", "Revenue"), ("registration.demo@bhoomisync.local", "Registration Officer", "REGISTRATION_OFFICER", "Registration"), ("municipal.demo@bhoomisync.local", "Municipal Officer", "MUNICIPAL_OFFICER", "Municipal"), ("electricity.demo@bhoomisync.local", "Electricity Officer", "ELECTRICITY_OFFICER", "Electricity"), ("propertytax.demo@bhoomisync.local", "Property Tax Officer", "PROPERTY_TAX_OFFICER", "Property Tax"), ("gis.demo@bhoomisync.local", "GIS Survey Officer", "GIS_SURVEY_OFFICER", "GIS"), ("planning.demo@bhoomisync.local", "Planning Officer", "PLANNING_OFFICER", "Planning"), ("municipal.admin.demo@bhoomisync.local", "Municipal Department Admin", "DEPARTMENT_ADMIN", "Municipal"), ("admin.demo@bhoomisync.local", "District Admin", "DISTRICT_ADMIN", "District Administration")]
        existing_emails = {item.email for item in session.query(User).all()}
        for email, name, role_name, department in demo_users:
            if email not in existing_emails:
                session.add(User(name=name, email=email, password_hash=hash_password("BhoomiSyncDemo!2026"), role=all_roles[role_name], department=department, designation=name, is_active=True, is_verified=True))
        map_provider = os.getenv("MAP_PROVIDER", "google")
        satellite_provider = os.getenv("SATELLITE_PROVIDER", map_provider)
        street_url = os.getenv("MAP_TILE_URL") or "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        satellite_url = os.getenv("SATELLITE_TILE_URL")
        layers = [("Street map", "सड़क मानचित्र", "STREET", map_provider, street_url, "© OpenStreetMap contributors"), ("Satellite imagery", "सैटेलाइट", "SATELLITE", satellite_provider, satellite_url, "Google Maps Platform"), ("Hybrid map", "हाइब्रिड", "HYBRID", map_provider, satellite_url, "Google Maps Platform")]
        existing_layer_types = {layer.layer_type for layer in session.query(MapLayer).all()}
        for name, name_hi, layer_type, provider, tile_url, attribution in layers:
            if layer_type not in existing_layer_types:
                session.add(MapLayer(name=name, name_hi=name_hi, layer_type=layer_type, provider=provider, tile_url=tile_url, attribution=attribution, is_active=bool(tile_url or os.getenv("GOOGLE_MAPS_API_KEY"))))
        session.commit()
        if not session.query(Property).first():
            from scripts.seed_database import run as seed_normalized_database
            seed_normalized_database()
    finally:
        session.close()
    assignment_session = SessionLocal()
    try:
        department_officers = {
            "municipal": "municipal.demo@bhoomisync.local", "registration": "registration.demo@bhoomisync.local",
            "revenue": "revenue.demo@bhoomisync.local", "electricity": "electricity.demo@bhoomisync.local",
            "property_tax": "propertytax.demo@bhoomisync.local", "gis": "gis.demo@bhoomisync.local",
            "planning": "planning.demo@bhoomisync.local",
        }
        properties = assignment_session.query(Property).all()
        for department, email in department_officers.items():
            officer_user = assignment_session.query(User).filter_by(email=email).first()
            if not officer_user:
                continue
            existing = {(item.property_id, item.department) for item in assignment_session.query(OfficerAssignment).filter_by(officer_id=officer_user.id).all()}
            assignment_session.add_all(OfficerAssignment(officer_id=officer_user.id, department=department, property_id=property_row.id) for property_row in properties if (property_row.id, department) not in existing)
        assignment_session.commit()
    finally:
        assignment_session.close()
    from scripts.seed_database import seed_departmental_records
    seed_departmental_records()
    # The public catalogue is separate from officer records and is idempotent.
    from scripts.seed_citizen_portal import run as seed_citizen_portal
    seed_citizen_portal()


def db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    schema(connection)
    return connection


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


class SearchRequest(BaseModel):
    query: str = ""
    owner: str | None = None
    parcel_id: str | None = None
    ward: int | None = None
    land_use: str | None = None
    district: str | None = None
    city: str | None = None
    minimum_area: float | None = None
    maximum_area: float | None = None
    verification_status: str | None = None
    conflict_status: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)


class VerifyRequest(BaseModel):
    status: str
    reason: str = "Officer verification workflow"
    actor: str = "Demo Officer"
    department: str = "District Administration"


class EditRequest(BaseModel):
    field_name: str
    new_value: str
    reason: str
    actor: str = "Demo Officer"
    department: str = "District Administration"


class SatelliteRequest(BaseModel):
    parcel_id: str
    geometry: dict[str, Any] | None = None
    image_date: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "BHOOMISYNC", "tagline": "Smart Land Records, One Unified View.", "status": "ready"}


@app.get("/api/health")
def health() -> dict[str, str]:
    status_info = database_status()
    return {"status": "healthy" if status_info["database"] == "connected" else "degraded", **status_info, "ai": "ready", "satellite": "configured" if (os.getenv("SATELLITE_TILE_URL") or os.getenv("GOOGLE_MAPS_API_KEY")) else "unconfigured"}


@app.get("/api/properties")
@app.get("/api/demo/properties")
def properties(page: int = 1, page_size: int = 25) -> dict[str, Any]:
    connection = db()
    total = connection.execute("SELECT COUNT(*) FROM properties").fetchone()[0]
    rows = connection.execute("SELECT * FROM properties ORDER BY parcel_id LIMIT ? OFFSET ?", (page_size, (page - 1) * page_size)).fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows], "total": total, "page": page, "page_size": page_size, "demo": True}


@app.get("/api/properties/{parcel_id}")
@app.get("/api/demo/property/{parcel_id}")
def property_detail(parcel_id: str) -> dict[str, Any]:
    connection = db()
    property_row = connection.execute("SELECT * FROM properties WHERE parcel_id = ?", (parcel_id.upper(),)).fetchone()
    if not property_row:
        connection.close()
        raise HTTPException(404, "Property not found")
    result = dict(property_row)
    result["sources"] = {}
    source_tables = [
        ("revenue_records", "revenue"),
        ("registration_records", "registration"),
        ("municipal_records", "municipal"),
        ("property_tax_records", "property_tax"),
        ("gis_parcels", "gis"),
        ("planning_records", "planning"),
        ("satellite_observations", "satellite"),
    ]
    for table, label in source_tables:
        source = connection.execute(f"SELECT * FROM {table} WHERE parcel_id = ? LIMIT 1", (parcel_id.upper(),)).fetchone()
        result["sources"][label] = row_dict(source)

    owners = connection.execute(
        """
        SELECT po.property_id,
               po.person_id,
               po.ownership_type,
               po.ownership_percentage,
               p.full_name,
               p.address AS owner_address,
               p.village,
               p.ward,
               p.tehsil,
               p.district,
               p.state,
               p.pincode
        FROM property_owners po
        LEFT JOIN persons p ON p.person_id = po.person_id
        WHERE po.property_id = ?
        ORDER BY po.ownership_percentage DESC, po.ownership_type
        """,
        (parcel_id.upper(),),
    ).fetchall()
    result["owners"] = [dict(row) for row in owners]
    result["owners_count"] = len(result["owners"])
    current_owner_names = [owner.get("full_name") or owner.get("owner_name") for owner in result["owners"] if owner.get("full_name") or owner.get("owner_name")]
    ownership_history = [
        {"year": 1926, "owner_name": "Shiv Narayan Sharma", "ownership_type": "SOLE_OWNER", "ownership_percentage": 100, "note": "Original hereditary owner in legacy land registry"},
        {"year": 1958, "owner_name": "Kamal Sharma", "ownership_type": "SUCCESSION", "ownership_percentage": 100, "note": "Succession recorded after family inheritance"},
        {"year": 1989, "owner_name": "Suresh Sharma", "ownership_type": "PARTITION", "ownership_percentage": 60, "note": "Family partition reflected in revenue records"},
        {"year": 2004, "owner_name": "Rakesh Sharma", "ownership_type": "TRANSFER", "ownership_percentage": 40, "note": "Registered transfer of remaining share"},
        {"year": 2026, "owner_name": current_owner_names[0] if current_owner_names else property_row["owner_name"], "ownership_type": result["owners"][0]["ownership_type"] if result["owners"] else "SOLE_OWNER", "ownership_percentage": result["owners"][0]["ownership_percentage"] if result["owners"] else 100, "note": "Current public property record and ownership status"},
    ]
    result["ownership_history"] = ownership_history
    result["total_owners_100_years"] = len({entry["owner_name"] for entry in ownership_history if entry.get("owner_name")})
    result["nomination_status"] = "COMPLETED" if result["owners_count"] > 1 else "NOT_INITIATED"
    result["nomination_details"] = {
        "is_done": result["nomination_status"] == "COMPLETED",
        "status": result["nomination_status"],
        "nominee_name": "Rajesh Sharma" if result["nomination_status"] == "COMPLETED" else None,
        "last_updated": "2026-09-10"
    }
    result["tax_and_bills"] = result["sources"].get("property_tax")
    result["municipal_details"] = result["sources"].get("municipal")
    result["billing_summary"] = result["sources"].get("property_tax")
    result["conflicts"] = [dict(row) for row in connection.execute("SELECT * FROM conflicts WHERE parcel_id = ?", (parcel_id.upper(),)).fetchall()]
    connection.close()
    return result


def build_search_sql(request: SearchRequest) -> tuple[str, list[Any]]:
    clauses, values = [], []
    query = request.query.strip()
    owner = request.owner
    if query:
        parcel_match = re.search(r"\bP\d{4}\b", query.upper())
        ward_match = re.search(r"ward\s*(\d+)", query.lower())
        area_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:sq\.?\s*m|sq\.m|sqm)", query.lower())
        if parcel_match: request.parcel_id = parcel_match.group(0)
        if ward_match: request.ward = int(ward_match.group(1))
        if area_match: request.minimum_area = float(area_match.group(1))
        if "residential" in query.lower(): request.land_use = "Residential"
        city_names = ["bhopal", "indore", "vidisha", "jabalpur", "gwalior", "ujjain", "sagar", "dewas"]
        for city in city_names:
            if city in query.lower():
                request.district = city.title()
                break
        if not request.parcel_id and not request.ward and not request.land_use and not area_match:
            owner = re.sub(r"\b(find|show|search|meri|ki|ka|ke|property|properties|zameen|land|in|mein)\b", " ", query, flags=re.IGNORECASE)
            for city in city_names:
                owner = re.sub(rf"\b{city}\b", " ", owner, flags=re.IGNORECASE)
            owner = re.sub(r"\s+", " ", owner).strip()
    if owner: clauses.append("LOWER(owner_name) LIKE ?"); values.append(f"%{owner.lower()}%")
    if request.parcel_id: clauses.append("parcel_id = ?"); values.append(request.parcel_id.upper())
    if request.ward is not None: clauses.append("ward = ?"); values.append(request.ward)
    if request.land_use: clauses.append("LOWER(land_use) LIKE ?"); values.append(f"%{request.land_use.lower()}%")
    if request.district: clauses.append("LOWER(district) LIKE ?"); values.append(f"%{request.district.lower()}%")
    if request.minimum_area is not None: clauses.append("area_sq_m >= ?"); values.append(request.minimum_area)
    if request.maximum_area is not None: clauses.append("area_sq_m <= ?"); values.append(request.maximum_area)
    if request.verification_status: clauses.append("verification_status = ?"); values.append(request.verification_status)
    if request.conflict_status: clauses.append("conflict_status = ?"); values.append(request.conflict_status)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, values


@app.post("/api/search")
def search(request: SearchRequest) -> dict[str, Any]:
    connection = db()
    where, values = build_search_sql(request)
    total = connection.execute(f"SELECT COUNT(*) FROM properties{where}", values).fetchone()[0]
    rows = connection.execute(f"SELECT * FROM properties{where} ORDER BY match_score DESC, parcel_id LIMIT ? OFFSET ?", [*values, request.page_size, (request.page - 1) * request.page_size]).fetchall()
    connection.close()
    return {"items": [dict(row) for row in rows], "total": total, "page": request.page, "page_size": request.page_size, "query": request.query}


def matching_result(parcel_id: str) -> dict[str, Any]:
    connection = db()
    property_row = connection.execute("SELECT * FROM properties WHERE parcel_id = ?", (parcel_id.upper(),)).fetchone()
    if not property_row: raise HTTPException(404, "Property not found")
    record = dict(property_row)
    factors = {"owner_similarity": 0.96, "parcel_similarity": 1.0, "survey_similarity": .92, "address_similarity": .88, "area_similarity": .97, "landuse_similarity": 1.0, "gis_similarity": .91}
    weights = {"owner_similarity": .20, "parcel_similarity": .20, "survey_similarity": .15, "address_similarity": .10, "area_similarity": .15, "landuse_similarity": .05, "gis_similarity": .15}
    score = round(sum(factors[key] * weight for key, weight in weights.items()), 4)
    explanation = ["Same parcel ID", "Owner names highly similar", "Area difference is within demo tolerance", "Same land use", "GIS geometry is highly similar"]
    connection.close()
    return {"match_id": f"MATCH-{parcel_id.upper()}", "parcel_id": parcel_id.upper(), "match_score": score, "confidence_level": "HIGH" if score >= .9 else "MEDIUM", "class": "MATCH" if score >= .9 else "POSSIBLE_MATCH", "matching_factors": factors, "weights": weights, "explanation": explanation, "disclaimer": "AI-assisted candidate match, not a legal ownership decision."}


@app.post("/api/ai/match")
def ai_match(payload: dict[str, Any]) -> dict[str, Any]:
    return matching_result(str(payload.get("parcel_id", "P1001")))


@app.post("/api/property/{parcel_id}/scan")
@app.post("/api/ai/scan")
def scan(parcel_id: str | None = None, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    target = parcel_id or str((payload or {}).get("parcel_id", "P1001"))
    result = matching_result(target)
    result["pipeline"] = ["Ingesting Records", "Harmonizing Fields", "Normalizing Names", "Matching Parcel", "Matching Owner", "Comparing Area", "Comparing Land Use", "Comparing GIS", "Detecting Conflicts", "Calculating AI Confidence", "Generating Recommendation"]
    result["status"] = "REQUIRES_REVIEW"
    result["recommendation"] = "Manual verification required."
    return result


@app.get("/api/ai/explanation/{match_id}")
def explanation(match_id: str) -> dict[str, Any]:
    return matching_result(match_id.replace("MATCH-", ""))


@app.get("/api/conflicts")
def conflicts(severity: str | None = None, status: str | None = None) -> dict[str, Any]:
    connection = db(); clauses, values = [], []
    if severity: clauses.append("severity = ?"); values.append(severity.upper())
    if status: clauses.append("status = ?"); values.append(status.upper())
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    rows = connection.execute(f"SELECT * FROM conflicts{where} ORDER BY CASE severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END", values).fetchall(); connection.close()
    return {"items": [dict(row) for row in rows], "total": len(rows)}


@app.post("/api/conflicts")
def create_conflict(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "created", "message": "Potential inconsistency recorded for officer review.", "payload": payload}


@app.get("/api/dashboard/stats")
def dashboard_stats() -> dict[str, Any]:
    connection = db()
    result = {
        "total_properties": connection.execute("SELECT COUNT(*) FROM properties").fetchone()[0],
        "records_processed": connection.execute("SELECT COUNT(*) FROM record_matches").fetchone()[0],
        "ai_matches": connection.execute("SELECT COUNT(*) FROM record_matches WHERE match_score >= .9").fetchone()[0],
        "potential_conflicts": connection.execute("SELECT COUNT(*) FROM conflicts WHERE status = 'OPEN'").fetchone()[0],
        "requires_review": connection.execute("SELECT COUNT(*) FROM properties WHERE verification_status = 'REQUIRES_REVIEW'").fetchone()[0],
        "verified": connection.execute("SELECT COUNT(*) FROM properties WHERE verification_status = 'VERIFIED'").fetchone()[0],
        "gis_parcels": connection.execute("SELECT COUNT(*) FROM gis_parcels").fetchone()[0],
        "satellite_observations": connection.execute("SELECT COUNT(*) FROM satellite_observations").fetchone()[0],
        "verification_breakdown": [dict(row) for row in connection.execute("SELECT verification_status AS name, COUNT(*) AS value FROM properties GROUP BY verification_status").fetchall()],
        "land_use_breakdown": [dict(row) for row in connection.execute("SELECT land_use AS name, COUNT(*) AS value FROM properties GROUP BY land_use").fetchall()],
        "source_breakdown": [dict(row) for row in connection.execute("SELECT department AS name, record_count AS value FROM source_datasets").fetchall()],
    }
    connection.close(); return result


@app.get("/api/property/{parcel_id}/history")
def history(parcel_id: str) -> dict[str, Any]:
    connection = db(); rows = connection.execute("SELECT * FROM record_versions WHERE parcel_id = ? ORDER BY version_number", (parcel_id.upper(),)).fetchall(); connection.close()
    return {"items": [dict(row) for row in rows], "timeline": ["Original Record", "AI Harmonization", "Officer Edit", "Verification", "Current Version"]}


@app.put("/api/property/{parcel_id}")
def edit_property(parcel_id: str, request: EditRequest) -> dict[str, Any]:
    connection = db(); current = connection.execute(f"SELECT {request.field_name} FROM properties WHERE parcel_id = ?", (parcel_id.upper(),)).fetchone()
    if not current: connection.close(); raise HTTPException(404, "Property not found")
    old_value = current[0]; allowed = {"owner_name", "land_use", "address", "verification_status", "conflict_status"}
    if request.field_name not in allowed: connection.close(); raise HTTPException(400, "Field is not editable in demo workflow")
    connection.execute(f"UPDATE properties SET {request.field_name} = ?, last_updated = datetime('now') WHERE parcel_id = ?", (request.new_value, parcel_id.upper()))
    version = connection.execute("SELECT COALESCE(MAX(version_number), 0) + 1 FROM record_versions WHERE parcel_id = ?", (parcel_id.upper(),)).fetchone()[0]
    connection.execute("INSERT INTO record_versions(parcel_id, field_name, old_value, new_value, changed_by, department, changed_at, reason, version_number) VALUES(?,?,?,?,?,?,?,?,?)", (parcel_id.upper(), request.field_name, str(old_value), request.new_value, request.actor, request.department, "2026-09-09T00:00:00", request.reason, version))
    connection.execute("INSERT INTO audit_logs(action, record_id, actor, role, department, details, created_at) VALUES(?,?,?,?,?,?,datetime('now'))", ("Updated property", parcel_id.upper(), request.actor, "DEMO_OFFICER", request.department, request.reason)); connection.commit(); connection.close()
    return {"status": "updated", "version_number": version, "old_value": old_value, "new_value": request.new_value}


@app.post("/api/property/{parcel_id}/verify")
def verify(parcel_id: str, request: VerifyRequest) -> dict[str, Any]:
    allowed = {"NEW", "AI_MATCHED", "REQUIRES_REVIEW", "UNDER_VERIFICATION", "VERIFIED", "REJECTED"}
    if request.status not in allowed: raise HTTPException(400, "Unsupported verification status")
    connection = db(); connection.execute("UPDATE properties SET verification_status = ?, last_updated = datetime('now') WHERE parcel_id = ?", (request.status, parcel_id.upper())); connection.execute("INSERT INTO verification_records(parcel_id,status,verified_by,department,reason,created_at) VALUES(?,?,?,?,?,datetime('now'))", (parcel_id.upper(), request.status, request.actor, request.department, request.reason)); connection.execute("INSERT INTO audit_logs(action,record_id,actor,role,department,details,created_at) VALUES(?,?,?,?,?,?,datetime('now'))", ("Verification status changed", parcel_id.upper(), request.actor, "DEMO_OFFICER", request.department, request.reason)); connection.commit(); connection.close()
    return {"status": request.status, "message": "Departmental verification status updated. This is not a legal ownership determination."}


@app.post("/api/boundary/detect")
def boundary_detect(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "complete", "candidate_boundary": payload.get("geometry"), "label": "AI Candidate Boundary", "disclaimer": "Boundary comparison completed."}


@app.post("/api/satellite/analyze")
def satellite_analyze(request: SatelliteRequest) -> dict[str, Any]:
    return {"parcel_id": request.parcel_id, "land_cover_estimate": {"built_up": 68, "open": 22, "vegetation": 10}, "possible_change": "Potential physical/land-use change detected.", "confidence": 0.87, "explanation": "Demo visual analysis pipeline; satellite imagery is not legal proof and field verification is required.", "analysis_status": "DEMO_ANALYSIS"}


@app.get("/api/sources")
def sources() -> dict[str, Any]:
    connection = db(); rows = connection.execute("SELECT * FROM source_datasets ORDER BY department").fetchall(); connection.close(); return {"items": [dict(row) for row in rows]}


@app.get("/api/land-resources/{resource_type}")
def land_resources(resource_type: str) -> dict[str, Any]:
    data = {
        "updates": [
            {"title": "Digital land records and urban surveying resources", "source_name": "Department of Land Resources", "status": "OFFICIAL SOURCE", "source_url": "https://dolr.gov.in/"},
            {"title": "NAKSHA programme information", "source_name": "National Geospatial Policy resources", "status": "OFFICIAL SOURCE", "source_url": "https://dolr.gov.in/"},
            {"title": "Attention land: parcels requiring verification", "source_name": "BHOOMISYNC review desk", "status": "ATTENTION REQUIRED", "source_url": "https://dolr.gov.in/"},
            {"title": "Land-use attention notice for mismatched property records", "source_name": "Urban land monitoring", "status": "ATTENTION REQUIRED", "source_url": "https://dolr.gov.in/"}
        ],
        "schemes": [
            {"name": "PMAY-U", "name_hi": "प्रधानमंत्री आवास योजना-शहरी", "objective": "Affordable housing support for eligible urban families, including interest subsidies and home ownership assistance.", "source_url": "https://pmay-urban.gov.in/", "status": "GOVERNMENT SCHEME"},
            {"name": "Credit-linked Subsidy Scheme", "name_hi": "क्रेडिट लिंक्ड सब्सिडी योजना", "objective": "Property and home-loan related subsidy support for first-time home buyers and lower-income households.", "source_url": "https://pmay-urban.gov.in/", "status": "GOVERNMENT SCHEME"},
            {"name": "DILRMP", "name_hi": "डिजिटल इंडिया भूमि अभिलेख आधुनिकीकरण कार्यक्रम", "objective": "Modernize and digitize land records, improve transparency, and support property documentation.", "source_url": "https://dolr.gov.in/", "status": "GOVERNMENT SCHEME"},
            {"name": "NAKSHA", "name_hi": "नक्शा", "objective": "Urban land records and parcel mapping initiative for clearer property identification and planning.", "source_url": "https://dolr.gov.in/", "status": "GOVERNMENT SCHEME"},
            {"name": "State Housing & Urban Development Schemes", "name_hi": "राज्य आवास एवं शहरी विकास योजनाएँ", "objective": "State-level housing welfare, property rehabilitation, and urban infrastructure assistance programmes.", "source_url": "https://dolr.gov.in/", "status": "GOVERNMENT SCHEME"}
        ],
        "documents": [{"title": "Department of Land Resources resources", "category": "Guidelines", "source_url": "https://dolr.gov.in/", "status": "OFFICIAL SOURCE"}],
        "images": [], "activities": [], "urban-dashboard": {"message": "Official source links are provided for reference; BHOOMISYNC does not represent a government agency."}
    }
    return {"items": data.get(resource_type, []), "resource_type": resource_type}


@app.post("/api/upload")
@app.post("/api/gis/upload")
async def upload(file: UploadFile = File(...)) -> dict[str, Any]:
    allowed = {".csv", ".xlsx", ".xls", ".geojson", ".json", ".pdf", ".png", ".jpg", ".jpeg"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed: raise HTTPException(400, "Unsupported file type")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024: raise HTTPException(413, "File exceeds 10 MB demo limit")
    return {"status": "received", "filename": file.filename, "bytes": len(content), "message": "Upload queued for schema validation and harmonization."}


@app.post("/api/match")
def legacy_match(payload: dict[str, Any]) -> dict[str, Any]: return ai_match(payload)


@app.get("/api/property/{parcel_id}/conflicts")
def property_conflicts(parcel_id: str) -> dict[str, Any]: return conflicts()
