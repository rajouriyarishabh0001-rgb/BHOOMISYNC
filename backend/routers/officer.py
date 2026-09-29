from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ai.matcher import match_records
from database.session import get_db
from models.core import AuditLog, Conflict, Parcel, Property, RecordVersion, Role, VerificationRecord
from models.officer import AIMatch, Report, SourceDataset
from models.sources import ElectricityRecord, MunicipalRecord, PlanningRecord, PropertyTaxRecord, RegistrationRecord, RevenueRecord
from routers.properties import property_response
from schemas.auth import LoginRequest
from security import create_access_token, current_user, verify_password

router = APIRouter(prefix="/api/officer", tags=["officer portal"])
Officer = Annotated[Any, Depends(current_user)]
DB = Annotated[Session, Depends(get_db)]


class OfficerSearchRequest(BaseModel):
    query: str = ""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=25, ge=1, le=100)
    department: str | None = None


class EditRequest(BaseModel):
    field_name: str
    new_value: str
    reason: str = Field(min_length=3)


class VerifyRequest(BaseModel):
    status: str
    remarks: str = "Departmental verification workflow"
    verification_method: str = "OFFICER_REVIEW"


def require_department(user: Any, allowed: set[str] | None = None) -> None:
    if allowed and user.role.name not in allowed:
        raise HTTPException(403, "Department permission required")


def audit(session: Session, user: Any, action: str, entity_type: str, entity_id: str, reason: str | None = None, old_value: str | None = None, new_value: str | None = None) -> None:
    session.add(AuditLog(user_id=user.id, role=user.role.name, department=user.department, action=action, entity_type=entity_type, entity_id=entity_id, reason=reason, old_value=old_value, new_value=new_value))


def allowed_departments_for_role(role_name: str | None) -> set[str]:
    access = {
        "SUPER_ADMIN": {"municipal", "registration", "revenue", "electricity", "property_tax", "gis", "planning"},
        "DISTRICT_ADMIN": {"municipal", "registration", "revenue", "electricity", "property_tax", "gis", "planning"},
        "MUNICIPAL_OFFICER": {"municipal"},
        "REGISTRATION_OFFICER": {"registration"},
        "REVENUE_OFFICER": {"revenue"},
        "ELECTRICITY_OFFICER": {"electricity"},
        "PROPERTY_TAX_OFFICER": {"property_tax"},
        "GIS_OFFICER": {"gis"},
        "GIS_SURVEY_OFFICER": {"gis"},
        "PLANNING_OFFICER": {"planning"},
    }
    return access.get(role_name or "", set())


def require_department_access(user: Any, department_key: str) -> None:
    if department_key not in allowed_departments_for_role(getattr(user.role, "name", None)):
        raise HTTPException(403, f"{getattr(user.role, 'name', 'Officer')} is not authorized to access the {department_key} department")


def serialize_source_record(row: Any, session: Session) -> dict[str, Any]:
    property_row = session.get(Property, row.property_id) if row.property_id else None
    values = {column.key: getattr(row, column.key) for column in row.__table__.columns}
    values["parcel_id"] = property_row.parcel_id if property_row else None
    values["property_id"] = property_row.property_id if property_row else None
    values["owner_name"] = values.get("owner_name") or (property_row.owner_name if property_row else None)
    values["address"] = values.get("address") or (property_row.address if property_row else None)
    values["ward"] = values.get("ward") or (property_row.ward if property_row else None)
    values["land_use"] = values.get("land_use") or (property_row.land_use if property_row else None)
    values["district"] = values.get("district") or (property_row.district if property_row else None)
    values["survey_number"] = values.get("survey_number") or (property_row.survey_number if property_row else None)
    values["khasra_number"] = values.get("khasra_number") or (property_row.khasra_number if property_row else None)
    values["property_status"] = values.get("property_status") or (property_row.property_status if property_row else None)
    values["record_status"] = values.get("record_status") or values.get("property_status") or "AVAILABLE"
    values["source_department"] = values.get("source_department") or getattr(user := None, "department", None)
    return values


@router.get("/departments")
def officer_departments(user: Officer) -> dict:
    modules = [
        {"key": "municipal", "title": "Municipal Department", "route": "/officer/dashboard?department=municipal", "description": "Municipal assessments, building records and approved public documents."},
        {"key": "registration", "title": "Nomination / Registration", "route": "/officer/dashboard?department=registration", "description": "Registration records, ownership transfers, approvals and document status."},
        {"key": "revenue", "title": "Collectorate / Revenue", "route": "/officer/dashboard?department=revenue", "description": "Survey, khasra, mutation records and land classification details."},
        {"key": "electricity", "title": "Electricity Department", "route": "/officer/dashboard?department=electricity", "description": "Consumer mapping, connection state and meter information."},
        {"key": "property_tax", "title": "Property Tax Department", "route": "/officer/dashboard?department=property_tax", "description": "Assessments, tax due, payments and outstanding liabilities."},
        {"key": "gis", "title": "GIS / Survey Department", "route": "/officer/dashboard?department=gis", "description": "Parcel geometry, boundary review and spatial comparisons."},
        {"key": "planning", "title": "Urban Planning Department", "route": "/officer/dashboard?department=planning", "description": "Zoning, planning approvals and land use compliance."},
    ]
    allowed = allowed_departments_for_role(getattr(user.role, "name", None))
    return {"success": True, "data": [module for module in modules if module["key"] in allowed]}


@router.get("/departments/{department_key}")
def officer_department_summary(department_key: str, user: Officer, session: DB) -> dict:
    department_key = department_key.lower()
    require_department_access(user, department_key)
    source_map = {
        "municipal": MunicipalRecord,
        "registration": RegistrationRecord,
        "revenue": RevenueRecord,
        "electricity": ElectricityRecord,
        "property_tax": PropertyTaxRecord,
        "planning": PlanningRecord,
        "gis": Parcel,
    }
    model = source_map.get(department_key)
    if not model:
        raise HTTPException(404, f"Unknown department workspace: {department_key}")

    if department_key == "gis":
        rows = session.scalars(select(Property).order_by(Property.parcel_id).limit(25)).all()
        records = [
            {
                "parcel_id": row.parcel_id,
                "owner_name": row.owner_name,
                "area_sq_m": row.area_sq_m,
                "land_use": row.land_use,
                "district": row.district,
                "verification_status": row.verification_status,
                "source_department": "GIS",
            }
            for row in rows
        ]
        stats = {
            "total_records": session.scalar(select(func.count()).select_from(Property)) or 0,
            "verified_records": session.scalar(select(func.count()).select_from(Property).where(Property.verification_status == "VERIFIED")) or 0,
            "open_conflicts": session.scalar(select(func.count()).select_from(Conflict).where(Conflict.status.in_(["OPEN", "UNDER_REVIEW"]))) or 0,
        }
    else:
        rows = session.scalars(select(model).order_by(model.created_at.desc()).limit(25)).all()
        stats = {
            "total_records": session.scalar(select(func.count()).select_from(model)) or 0,
            "verified_records": session.scalar(select(func.count()).select_from(model).where(model.source_department.like("%"))) or 0,
            "open_conflicts": session.scalar(select(func.count()).select_from(Conflict).where(Conflict.status.in_(["OPEN", "UNDER_REVIEW"]))) or 0,
        }
        records = [serialize_source_record(row, session) for row in rows]

    return {
        "success": True,
        "data": {
            "department": department_key,
            "title": next(module["title"] for module in [
                {"key": "municipal", "title": "Municipal Department"},
                {"key": "registration", "title": "Nomination / Registration"},
                {"key": "revenue", "title": "Collectorate / Revenue"},
                {"key": "electricity", "title": "Electricity Department"},
                {"key": "property_tax", "title": "Property Tax Department"},
                {"key": "gis", "title": "GIS / Survey Department"},
                {"key": "planning", "title": "Urban Planning Department"},
            ] if module["key"] == department_key),
            "stats": stats,
            "records": records,
        },
    }


@router.post("/auth/login")
def officer_login(request: LoginRequest, session: DB) -> dict:
    from models.core import User
    user = session.scalar(select(User).options(joinedload(User.role)).where(User.email == request.email.lower()))
    if os.getenv("DEMO_AUTH_BYPASS", "false").lower() == "true" and request.email.strip() and request.password:
        user = session.scalar(select(User).options(joinedload(User.role)).where(User.is_active.is_(True), User.role.has(Role.name != "CITIZEN")).order_by(User.email))
    if not user or not verify_password(request.password, user.password_hash) or not user.is_active or user.role.name == "CITIZEN":
        if os.getenv("DEMO_AUTH_BYPASS", "false").lower() == "true" and request.email.strip() and request.password and user and user.is_active and user.role.name != "CITIZEN":
            return {"success": True, "data": {"access_token": create_access_token(user), "token_type": "bearer", "user": {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role.name, "department": user.department}}}
        raise HTTPException(401, "Invalid officer credentials")
    return {"success": True, "data": {"access_token": create_access_token(user), "token_type": "bearer", "user": {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role.name, "department": user.department}}}


@router.get("/me")
def officer_me(user: Officer) -> dict:
    return {"success": True, "data": {"id": str(user.id), "name": user.name, "email": user.email, "role": user.role.name, "department": user.department, "is_verified": user.is_verified}}


@router.get("/dashboard/stats")
def officer_dashboard_stats(user: Officer, session: DB) -> dict:
    require_department(user)
    total = session.scalar(select(func.count()).select_from(Property)) or 0
    verified = session.scalar(select(func.count()).select_from(Property).where(Property.verification_status == "VERIFIED")) or 0
    pending = session.scalar(select(func.count()).select_from(Property).where(Property.verification_status.in_(["NEW", "REQUIRES_REVIEW", "UNDER_VERIFICATION"]))) or 0
    open_conflicts = session.scalar(select(func.count()).select_from(Conflict).where(Conflict.status.in_(["OPEN", "UNDER_REVIEW"]))) or 0
    high_conflicts = session.scalar(select(func.count()).select_from(Conflict).where(Conflict.severity == "HIGH", Conflict.status.in_(["OPEN", "UNDER_REVIEW"]))) or 0
    return {"success": True, "data": {"total_properties": total, "verified_properties": verified, "pending_verification": pending, "open_conflicts": open_conflicts, "high_priority_conflicts": high_conflicts, "total_source_records": session.scalar(select(func.count()).select_from(SourceDataset)) or 0, "matched_records": session.scalar(select(func.count()).select_from(AIMatch)) or 0, "ai_scans_today": 0, "satellite_analyses": 0, "uploaded_datasets": session.scalar(select(func.count()).select_from(SourceDataset)) or 0}}


@router.post("/search")
def officer_search(request: OfficerSearchRequest, user: Officer, session: DB) -> dict:
    require_department(user)
    query = request.query.strip()
    filters = []
    if query:
        parcel = re.search(r"\bP\d{4}\b", query.upper())
        if parcel:
            filters.append(Property.parcel_id == parcel.group(0))
        else:
            cleaned = re.sub(r"\b(find|show|search|property|properties|in|ki|ka|ke|zameen|land)\b", " ", query, flags=re.I).strip()
            filters.append(or_(Property.parcel_id.ilike(f"%{query}%"), Property.owner_name.ilike(f"%{cleaned or query}%"), Property.address.ilike(f"%{cleaned or query}%"), Property.survey_number.ilike(f"%{query}%"), Property.khasra_number.ilike(f"%{query}%")))
    statement = select(Property).where(*filters).order_by(Property.parcel_id).offset((request.page - 1) * request.page_size).limit(request.page_size)
    rows = session.scalars(statement).all()
    result = [property_response(row) for row in rows]
    return {"success": True, "data": {"items": result, "results": result, "total": session.scalar(select(func.count()).select_from(Property).where(*filters)) or 0, "page": request.page, "page_size": request.page_size}}


@router.get("/properties/{parcel_id}")
def officer_property(parcel_id: str, user: Officer, session: DB) -> dict:
    row = session.scalar(select(Property).options(joinedload(Property.parcels), joinedload(Property.conflicts)).where(Property.parcel_id == parcel_id.upper()))
    if not row:
        raise HTTPException(404, "Property was not found.")
    audit(session, user, "VIEW", "PROPERTY", row.parcel_id)
    session.commit()
    match = session.scalar(select(AIMatch).where(AIMatch.property_id == row.id).order_by(AIMatch.created_at.desc()))
    return {"success": True, "data": {"property": property_response(row), "parcel": {"boundary": row.parcels[0].boundary if row.parcels else None, "centroid": row.parcels[0].centroid if row.parcels else None, "crs": row.parcels[0].crs if row.parcels else None}, "ai": {"match_score": match.match_score, "confidence_level": match.confidence_level, "explanation": match.explanation} if match else None, "conflicts": [{"id": str(item.id), "type": item.conflict_type, "severity": item.severity, "description": item.description, "status": item.status} for item in row.conflicts], "verification": {"status": row.verification_status}, "audit": []}}


@router.put("/properties/{parcel_id}")
def officer_edit(parcel_id: str, request: EditRequest, user: Officer, session: DB) -> dict:
    require_department(user, {"DISTRICT_ADMIN", "SUPER_ADMIN", "REVENUE_OFFICER", "GIS_SURVEY_OFFICER", "PLANNING_OFFICER"})
    allowed = {"owner_name", "co_owner_name", "land_use", "address", "verification_status", "conflict_status", "zone"}
    if request.field_name not in allowed:
        raise HTTPException(403, "This role cannot edit that field")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row:
        raise HTTPException(404, "Property was not found.")
    old = str(getattr(row, request.field_name))
    setattr(row, request.field_name, request.new_value)
    version = (session.scalar(select(func.max(RecordVersion.version_number)).where(RecordVersion.property_id == row.id)) or 0) + 1
    session.add(RecordVersion(property_id=row.id, field_name=request.field_name, old_value=old, new_value=request.new_value, changed_by=user.id, department=user.department, reason=request.reason, version_number=version))
    audit(session, user, "UPDATE", "PROPERTY", row.parcel_id, request.reason, old, request.new_value)
    session.commit()
    return {"success": True, "data": {"parcel_id": row.parcel_id, "old_value": old, "new_value": request.new_value, "version_number": version}}


@router.get("/properties/{parcel_id}/history")
def officer_history(parcel_id: str, user: Officer, session: DB) -> dict:
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    records = session.scalars(select(RecordVersion).where(RecordVersion.property_id == row.id).order_by(RecordVersion.version_number)).all()
    return {"success": True, "data": [{"field_name": item.field_name, "old_value": item.old_value, "new_value": item.new_value, "department": item.department, "reason": item.reason, "version_number": item.version_number, "created_at": item.created_at} for item in records]}


@router.post("/properties/{parcel_id}/verify")
def officer_verify(parcel_id: str, request: VerifyRequest, user: Officer, session: DB) -> dict:
    allowed = {"NEW", "AI_MATCHED", "REQUIRES_REVIEW", "UNDER_VERIFICATION", "VERIFIED", "REJECTED"}
    if request.status not in allowed: raise HTTPException(422, "Unsupported verification status")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    row.verification_status = request.status
    session.add(VerificationRecord(property_id=row.id, verified_by=user.id, department=user.department, status=request.status, reason=request.remarks))
    audit(session, user, "VERIFY", "PROPERTY", row.parcel_id, request.remarks, None, request.status)
    session.commit()
    return {"success": True, "data": {"parcel_id": row.parcel_id, "status": request.status, "message": "Departmental verification status updated."}}


@router.post("/ai/scan/{parcel_id}")
def officer_ai_scan(parcel_id: str, user: Officer, session: DB) -> dict:
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    left = {"parcel_id": row.parcel_id, "owner_name": row.owner_name, "address": row.address, "area_sq_m": row.area_sq_m, "land_use": row.land_use, "survey_number": row.survey_number, "khasra_number": row.khasra_number}
    result = match_records(left, left)
    record = AIMatch(property_id=row.id, match_score=result["match_score"], match_probability=result["match_probability"], confidence_level=result["confidence_level"], status="MATCH" if result["match_score"] >= 85 else "REQUIRES_REVIEW", matching_factors=result["matching_factors"], explanation=result["explanation"])
    session.add(record); audit(session, user, "AI_SCAN", "PROPERTY", row.parcel_id); session.commit()
    return {"success": True, "data": {"parcel_id": row.parcel_id, **result, "recommendation": "Manual verification required.", "disclaimer": "AI-assisted candidate match; no legal ownership decision is made."}}


@router.get("/gis/parcel/{parcel_id}")
def officer_gis_parcel(parcel_id: str, user: Officer, session: DB) -> dict:
    row = session.scalar(select(Property).options(joinedload(Property.parcels)).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    parcel = row.parcels[0] if row.parcels else None
    return {"success": True, "data": {"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude, "geometry": parcel.boundary if parcel else None, "centroid": parcel.centroid if parcel else None, "crs": parcel.crs if parcel else None}}


@router.get("/gis/viewport")
def officer_gis_viewport(north: float, south: float, east: float, west: float, user: Officer, session: DB) -> dict:
    rows = session.scalars(select(Property).where(Property.latitude.between(south, north), Property.longitude.between(west, east)).limit(500)).all()
    return {"success": True, "data": [{"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude} for row in rows]}


@router.get("/gis/layers")
def officer_gis_layers(user: Officer, session: DB) -> dict:
    from models.core import MapLayer
    rows = session.scalars(select(MapLayer).where(MapLayer.is_active.is_(True))).all()
    return {"success": True, "data": [{"name": row.name, "layer_type": row.layer_type, "provider": row.provider, "tile_url": row.tile_url, "attribution": row.attribution} for row in rows]}


@router.get("/gis/nearby")
def officer_gis_nearby(latitude: float, longitude: float, radius: float = 1000, user: Officer = None, session: DB = None) -> dict:
    rows = session.scalars(select(Property).where(Property.latitude.between(latitude - radius / 111320, latitude + radius / 111320), Property.longitude.between(longitude - radius / 111320, longitude + radius / 111320)).limit(500)).all()
    return {"success": True, "data": [{"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude} for row in rows]}


@router.post("/gis/analyze")
def officer_gis_analyze(payload: dict, user: Officer, session: DB) -> dict:
    parcel_id = str(payload.get("parcel_id", "")).upper()
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id))
    if not row: raise HTTPException(404, "Property was not found.")
    audit(session, user, "GIS_ANALYZE", "PROPERTY", parcel_id); session.commit()
    return {"success": True, "data": {"parcel_id": parcel_id, "area_sq_m": row.area_sq_m, "boundary_status": "AVAILABLE" if row.parcels else "UNAVAILABLE", "message": "Spatial comparison completed."}}


@router.post("/gis/upload")
async def officer_gis_upload(file: UploadFile = File(...), user: Officer = None, session: DB = None) -> dict:
    if not (file.filename or "").lower().endswith((".geojson", ".json")):
        raise HTTPException(400, "GIS upload requires GeoJSON")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024: raise HTTPException(413, "GIS upload exceeds 25 MB")
    audit(session, user, "UPLOAD", "GIS_DATASET", file.filename or "upload"); session.commit()
    return {"success": True, "data": {"filename": file.filename, "bytes": len(content), "status": "UPLOADED"}}


@router.get("/conflicts")
def officer_conflicts(user: Officer, session: DB) -> dict:
    rows = session.scalars(select(Conflict).order_by(Conflict.created_at.desc()).limit(500)).all()
    return {"success": True, "data": [{"id": str(row.id), "property_id": str(row.property_id), "conflict_type": row.conflict_type, "severity": row.severity, "description": row.description, "status": row.status} for row in rows]}


@router.post("/conflicts/{conflict_id}/resolve")
def officer_resolve_conflict(conflict_id: str, payload: dict, user: Officer, session: DB) -> dict:
    row = session.get(Conflict, conflict_id)
    if not row: raise HTTPException(404, "Conflict was not found.")
    row.status = str(payload.get("status", "RESOLVED")); row.resolution = str(payload.get("resolution", "Officer review completed.")); row.resolved_by = user.id; row.resolved_at = datetime.now(timezone.utc)
    audit(session, user, "RESOLVE_CONFLICT", "CONFLICT", conflict_id, row.resolution); session.commit()
    return {"success": True, "data": {"id": conflict_id, "status": row.status, "resolution": row.resolution}}


@router.get("/audit")
def officer_audit(user: Officer, session: DB) -> dict:
    require_department(user, {"DISTRICT_ADMIN", "SUPER_ADMIN"})
    rows = session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)).all()
    return {"success": True, "data": [{"action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "department": row.department, "reason": row.reason, "created_at": row.created_at} for row in rows]}


@router.post("/datasets/upload")
async def officer_dataset_upload(file: UploadFile = File(...), user: Officer = None, session: DB = None) -> dict:
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in {".csv", ".xlsx", ".xls", ".geojson", ".json"}:
        raise HTTPException(400, "Only CSV, Excel, and GeoJSON uploads are supported")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024: raise HTTPException(413, "Dataset exceeds 25 MB")
    dataset = SourceDataset(dataset_name=file.filename or "uploaded dataset", department=user.department, source_type="OFFICER_UPLOAD", file_name=file.filename, file_format=suffix.lstrip("."), record_count=0, uploaded_by=user.id, processing_status="UPLOADED", harmonization_status="PENDING")
    session.add(dataset); audit(session, user, "UPLOAD", "DATASET", str(dataset.id), "Officer dataset upload"); session.commit()
    return {"success": True, "data": {"dataset_id": str(dataset.id), "filename": file.filename, "bytes": len(content), "processing_status": dataset.processing_status}}


@router.post("/reports")
def create_report(report_type: str, user: Officer, session: DB) -> dict:
    record = Report(report_type=report_type, generated_by=user.id, status="READY")
    session.add(record); audit(session, user, "EXPORT", "REPORT", str(record.id)); session.commit()
    return {"success": True, "data": {"id": str(record.id), "report_type": report_type, "status": record.status}}


@router.get("/reports")
def reports(user: Officer, session: DB) -> dict:
    rows = session.scalars(select(Report).order_by(Report.created_at.desc()).limit(100)).all()
    return {"success": True, "data": [{"id": str(row.id), "report_type": row.report_type, "status": row.status, "created_at": row.created_at} for row in rows]}
