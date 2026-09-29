from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from ai.matcher import match_records
from database.session import get_db
from models.core import AuditLog, Conflict, Parcel, Property, RecordVersion, Role, User, VerificationRecord
from models.officer import AIMatch, OfficerAssignment, Permission, Report, RolePermission, SourceDataset
from models.sources import ElectricityRecord, MunicipalRecord, PlanningRecord, PropertyTaxRecord, RegistrationRecord, RevenueRecord
from routers.properties import property_response
from schemas.auth import LoginRequest
from security import create_access_token, current_user, hash_password, verify_password

router = APIRouter(prefix="/api/officer", tags=["officer portal"])
def authenticated_officer(user: Annotated[Any, Depends(current_user)]) -> Any:
    if not user.role or user.role.name == "CITIZEN":
        raise HTTPException(403, "Officer identity required")
    return user

Officer = Annotated[Any, Depends(authenticated_officer)]
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


class OfficerCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    email: str
    password: str = Field(min_length=10)
    designation: str | None = Field(default=None, max_length=120)


class AssignmentRequest(BaseModel):
    officer_id: str
    property_id: str
    from_officer_id: str | None = None


class ActiveStatusRequest(BaseModel):
    is_active: bool


class ConflictFlagRequest(BaseModel):
    description: str = Field(min_length=5, max_length=2000)
    conflict_type: str = Field(default="OFFICER_FLAG", max_length=50)
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH)$")


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
        "DEPARTMENT_ADMIN": set(),
    }
    return access.get(role_name or "", set())


DEPARTMENT_ALIASES = {
    "municipal": "municipal", "registration": "registration", "revenue": "revenue",
    "electricity": "electricity", "property tax": "property_tax", "property_tax": "property_tax",
    "gis": "gis", "gis survey": "gis", "planning": "planning",
}


def department_key(user: Any) -> str | None:
    return DEPARTMENT_ALIASES.get((getattr(user, "department", "") or "").strip().lower())


def is_department_admin(user: Any) -> bool:
    return getattr(user.role, "name", None) == "DEPARTMENT_ADMIN"


def is_scoped_admin(user: Any) -> bool:
    return getattr(user.role, "name", None) in {"DISTRICT_ADMIN", "SUPER_ADMIN", "DEPARTMENT_ADMIN"}


def assigned_property_ids(user: Any, department: str | None = None):
    statement = select(OfficerAssignment.property_id).where(OfficerAssignment.is_active.is_(True))
    if department:
        statement = statement.where(OfficerAssignment.department == department)
    if not is_scoped_admin(user):
        statement = statement.where(OfficerAssignment.officer_id == user.id)
    elif is_department_admin(user):
        statement = statement.where(OfficerAssignment.department == department_key(user))
    return statement


def assigned_record_count(user: Any, session: Session, department: str | None = None) -> int:
    statement = select(func.count()).select_from(OfficerAssignment).where(OfficerAssignment.is_active.is_(True))
    if department:
        statement = statement.where(OfficerAssignment.department == department)
    if not is_scoped_admin(user):
        statement = statement.where(OfficerAssignment.officer_id == user.id)
    elif is_department_admin(user):
        statement = statement.where(OfficerAssignment.department == department_key(user))
    return session.scalar(statement) or 0


def require_department_access(user: Any, requested_department: str) -> None:
    role_name = getattr(user.role, "name", None)
    allowed = allowed_departments_for_role(role_name)
    if role_name == "DEPARTMENT_ADMIN":
        assigned_department = department_key(user)
        allowed = {assigned_department} if assigned_department else set()
    if requested_department not in allowed:
        raise HTTPException(403, f"{getattr(user.role, 'name', 'Officer')} is not authorized to access the {requested_department} department")


def require_assigned_property(user: Any, session: Session, property_row: Property, department: str | None = None) -> None:
    if is_scoped_admin(user):
        if is_department_admin(user) and department and department != department_key(user):
            raise HTTPException(403, "Department administrator cannot access another department")
        return
    assignment = select(OfficerAssignment.id).where(
        OfficerAssignment.officer_id == user.id,
        OfficerAssignment.property_id == property_row.id,
        OfficerAssignment.is_active.is_(True),
    )
    if department:
        assignment = assignment.where(OfficerAssignment.department == department)
    if session.scalar(assignment) is None:
        raise HTTPException(403, "This property is not assigned to the authenticated officer")


def require_permission(user: Any, session: Session, permission_code: str) -> None:
    if user.role.name == "SUPER_ADMIN":
        return
    permission = select(RolePermission.id).join(Permission, Permission.id == RolePermission.permission_id).where(RolePermission.role_id == user.role_id, Permission.code == permission_code)
    if session.scalar(permission) is None:
        raise HTTPException(403, f"Missing permission: {permission_code}")


def require_department_admin(user: Any, session: Session) -> str:
    if user.role.name != "DEPARTMENT_ADMIN":
        raise HTTPException(403, "Department administrator permission required")
    department = department_key(user)
    if not department:
        raise HTTPException(403, "Department administrator must have a valid department")
    require_permission(user, session, "USER_MANAGE")
    return department


def serialize_source_record(row: Any, session: Session) -> dict[str, Any]:
    property_row = session.get(Property, row.property_id) if row.property_id else None
    values = {column.key: getattr(row, column.key) for column in row.__table__.columns}
    values.update({key: value for key, value in (row.original_values or {}).items() if key not in values})
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
    if getattr(user.role, "name", None) == "DEPARTMENT_ADMIN" and department_key(user):
        allowed = {department_key(user)}
    return {"success": True, "data": [module for module in modules if module["key"] in allowed]}


@router.get("/departments/{department_key}")
def officer_department_summary(department_key: str, user: Officer, session: DB) -> dict:
    department_key = department_key.lower()
    require_department_access(user, department_key)
    require_permission(user, session, "RECORD_VIEW")
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

    property_scope = assigned_property_ids(user, department_key)
    if department_key == "gis":
        rows = session.scalars(select(Property).where(Property.id.in_(property_scope)).order_by(Property.parcel_id).limit(25)).all()
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
            "total_records": session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope))) or 0,
            "verified_records": session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope), Property.verification_status == "VERIFIED")) or 0,
            "open_conflicts": session.scalar(select(func.count()).select_from(Conflict).where(Conflict.status.in_(["OPEN", "UNDER_REVIEW"]), Conflict.property_id.in_(property_scope))) or 0,
        }
        stats["boundary_variations"] = stats["open_conflicts"]
        stats["missing_geometry"] = session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope), ~Property.parcels.any(Parcel.boundary.is_not(None)))) or 0
    else:
        rows = session.scalars(select(model).where(model.property_id.in_(property_scope)).order_by(model.created_at.desc()).limit(25)).all()
        total_records = session.scalar(select(func.count()).select_from(model).where(model.property_id.in_(property_scope))) or 0
        verified_records = session.scalar(select(func.count(func.distinct(Property.id))).select_from(model).join(Property, Property.id == model.property_id).where(Property.id.in_(property_scope), Property.verification_status == "VERIFIED")) or 0
        recent_records = session.scalar(select(func.count()).select_from(model).where(model.property_id.in_(property_scope), model.updated_at >= datetime.now(timezone.utc) - timedelta(days=30))) or 0
        stats = {
            "total_records": total_records,
            "verified_records": verified_records,
            "pending_verification": max(0, total_records - verified_records),
            "recently_updated": recent_records,
            "open_conflicts": session.scalar(select(func.count()).select_from(Conflict).where(Conflict.status.in_(["OPEN", "UNDER_REVIEW"]), Conflict.property_id.in_(property_scope))) or 0,
        }
        if department_key == "registration":
            stats["pending_documents"] = session.scalar(select(func.count()).select_from(RegistrationRecord).where(RegistrationRecord.property_id.in_(property_scope), RegistrationRecord.document_number.is_(None))) or 0
        elif department_key == "revenue":
            stats["pending_mutation"] = session.scalar(select(func.count()).select_from(RevenueRecord).where(RevenueRecord.property_id.in_(property_scope), or_(RevenueRecord.mutation_status.is_(None), RevenueRecord.mutation_status.notin_(["VERIFIED", "COMPLETED"])))) or 0
            stats["missing_information"] = session.scalar(select(func.count()).select_from(RevenueRecord).where(RevenueRecord.property_id.in_(property_scope), or_(RevenueRecord.owner_name.is_(None), RevenueRecord.area_original.is_(None)))) or 0
        elif department_key == "electricity":
            stats["active_connections"] = session.scalar(select(func.count()).select_from(ElectricityRecord).where(ElectricityRecord.property_id.in_(property_scope), func.upper(ElectricityRecord.connection_status) == "ACTIVE")) or 0
            stats["billing_issues"] = 0
        elif department_key == "property_tax":
            stats["tax_assessed"] = session.scalar(select(func.count()).select_from(PropertyTaxRecord).where(PropertyTaxRecord.property_id.in_(property_scope), PropertyTaxRecord.tax_amount.is_not(None))) or 0
            stats["pending_payments"] = session.scalar(select(func.count()).select_from(PropertyTaxRecord).where(PropertyTaxRecord.property_id.in_(property_scope), or_(PropertyTaxRecord.tax_status.is_(None), func.upper(PropertyTaxRecord.tax_status) != "PAID"))) or 0
            stats["total_due"] = 0
        elif department_key == "planning":
            stats["planning_reviews"] = total_records
            stats["pending_approvals"] = max(0, total_records - verified_records)
        records = [serialize_source_record(row, session) for row in rows]

    audit(session, user, "VIEW", "DEPARTMENT", department_key)
    session.commit()
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
    if not user or not verify_password(request.password, user.password_hash) or not user.is_active or user.role.name == "CITIZEN":
        raise HTTPException(401, "Invalid officer credentials")
    user.last_login = datetime.now(timezone.utc)
    session.add(AuditLog(user_id=user.id, role=user.role.name, department=user.department, action="LOGIN", entity_type="OFFICER", entity_id=str(user.id)))
    session.commit()
    permissions = session.scalars(select(Permission.code).join(RolePermission, RolePermission.permission_id == Permission.id).where(RolePermission.role_id == user.role_id).order_by(Permission.code)).all()
    assigned_count = assigned_record_count(user, session, department_key(user))
    officer_profile = {"id": str(user.id), "officer_id": str(user.id), "name": user.name, "email": user.email, "role": user.role.name, "department": user.department, "department_key": department_key(user), "designation": user.designation or user.role.name.replace("_", " ").title(), "permissions": permissions, "assigned_record_count": assigned_count}
    return {"success": True, "data": {"access_token": create_access_token(user), "token_type": "bearer", "user": officer_profile, "officer": officer_profile}}


@router.get("/me")
def officer_me(user: Officer, session: DB) -> dict:
    permissions = session.scalars(select(Permission.code).join(RolePermission, RolePermission.permission_id == Permission.id).where(RolePermission.role_id == user.role_id).order_by(Permission.code)).all()
    assignment_count = assigned_record_count(user, session, department_key(user))
    return {"success": True, "data": {"id": str(user.id), "officer_id": str(user.id), "name": user.name, "email": user.email, "role": user.role.name, "department": user.department, "department_key": department_key(user), "permissions": permissions, "designation": user.designation or user.role.name.replace("_", " ").title(), "assigned_record_count": assignment_count, "is_verified": user.is_verified}}


@router.post("/auth/logout")
def officer_logout(user: Officer, session: DB) -> dict:
    audit(session, user, "LOGOUT", "OFFICER", str(user.id))
    session.commit()
    return {"success": True, "message": "Officer session ended"}


@router.get("/property/{property_id}")
def officer_unified_property(property_id: str, user: Officer, session: DB) -> dict:
    require_permission(user, session, "PROPERTY_VIEW")
    row = session.scalar(select(Property).where(or_(Property.property_id == property_id, Property.parcel_id == property_id.upper())))
    if not row:
        raise HTTPException(404, "Property was not found.")
    departments = allowed_departments_for_role(user.role.name)
    if user.role.name == "DEPARTMENT_ADMIN" and department_key(user):
        departments = {department_key(user)}
    if not is_scoped_admin(user):
        assigned = set(session.scalars(select(OfficerAssignment.department).where(OfficerAssignment.officer_id == user.id, OfficerAssignment.property_id == row.id, OfficerAssignment.is_active.is_(True))).all())
        departments &= assigned
    if not departments:
        raise HTTPException(403, "This property is not assigned to the authenticated officer")
    source_map = {"municipal": MunicipalRecord, "registration": RegistrationRecord, "revenue": RevenueRecord, "electricity": ElectricityRecord, "property_tax": PropertyTaxRecord, "planning": PlanningRecord}
    sections = {}
    for key in sorted(departments):
        assignment_owner = session.scalar(select(User.name).join(OfficerAssignment, OfficerAssignment.officer_id == User.id).where(OfficerAssignment.property_id == row.id, OfficerAssignment.department == key, OfficerAssignment.is_active.is_(True)).order_by(OfficerAssignment.created_at.desc()).limit(1))
        section_meta = {"record_status": row.property_status, "assigned_officer": assignment_owner, "last_updated": row.updated_at, "verification_status": row.verification_status}
        if key == "gis":
            sections[key] = {**section_meta, "records": [{"parcel_id": row.parcel_id, "area_sq_m": row.area_sq_m, "land_use": row.land_use}]}
            continue
        model = source_map[key]
        records = session.scalars(select(model).where(model.property_id == row.id)).all()
        last_updated = max((record.updated_at for record in records if record.updated_at), default=row.updated_at)
        sections[key] = {**section_meta, "last_updated": last_updated, "records": [serialize_source_record(record, session) for record in records]}
    audit(session, user, "VIEW", "PROPERTY", row.parcel_id)
    session.commit()
    return {"success": True, "data": {"property": property_response(row), "departments": sections}}


@router.get("/dashboard/stats")
def officer_dashboard_stats(user: Officer, session: DB) -> dict:
    require_department(user)
    require_permission(user, session, "PROPERTY_VIEW")
    property_scope = assigned_property_ids(user, department_key(user))
    total = session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope))) or 0
    verified = session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope), Property.verification_status == "VERIFIED")) or 0
    pending = session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope), Property.verification_status.in_(["NEW", "REQUIRES_REVIEW", "UNDER_VERIFICATION"]))) or 0
    open_conflicts = session.scalar(select(func.count()).select_from(Conflict).where(Conflict.property_id.in_(property_scope), Conflict.status.in_(["OPEN", "UNDER_REVIEW"]))) or 0
    high_conflicts = session.scalar(select(func.count()).select_from(Conflict).where(Conflict.property_id.in_(property_scope), Conflict.severity == "HIGH", Conflict.status.in_(["OPEN", "UNDER_REVIEW"]))) or 0
    source_scope = select(func.count()).select_from(SourceDataset)
    if user.role.name not in {"DISTRICT_ADMIN", "SUPER_ADMIN"}:
        source_scope = source_scope.where(func.lower(SourceDataset.department) == (user.department or "").lower())
    matched_scope = select(func.count()).select_from(AIMatch).where(AIMatch.property_id.in_(property_scope))
    return {"success": True, "data": {"total_properties": total, "verified_properties": verified, "pending_verification": pending, "open_conflicts": open_conflicts, "high_priority_conflicts": high_conflicts, "total_source_records": session.scalar(source_scope) or 0, "matched_records": session.scalar(matched_scope) or 0, "ai_scans_today": 0, "satellite_analyses": 0, "uploaded_datasets": session.scalar(source_scope) or 0}}


@router.post("/search")
def officer_search(request: OfficerSearchRequest, user: Officer, session: DB) -> dict:
    require_department(user)
    require_permission(user, session, "PROPERTY_VIEW")
    query = request.query.strip()
    filters = []
    if query:
        parcel = re.search(r"\bP\d{4}\b", query.upper())
        if parcel:
            filters.append(Property.parcel_id == parcel.group(0))
        else:
            cleaned = re.sub(r"\b(find|show|search|property|properties|in|ki|ka|ke|zameen|land)\b", " ", query, flags=re.I).strip()
            filters.append(or_(Property.parcel_id.ilike(f"%{query}%"), Property.owner_name.ilike(f"%{cleaned or query}%"), Property.address.ilike(f"%{cleaned or query}%"), Property.survey_number.ilike(f"%{query}%"), Property.khasra_number.ilike(f"%{query}%")))
    property_scope = assigned_property_ids(user, department_key(user))
    statement = select(Property).where(Property.id.in_(property_scope), *filters).order_by(Property.parcel_id).offset((request.page - 1) * request.page_size).limit(request.page_size)
    rows = session.scalars(statement).all()
    result = [property_response(row) for row in rows]
    return {"success": True, "data": {"items": result, "results": result, "total": session.scalar(select(func.count()).select_from(Property).where(Property.id.in_(property_scope), *filters)) or 0, "page": request.page, "page_size": request.page_size}}


@router.get("/properties/{parcel_id}")
def officer_property(parcel_id: str, user: Officer, session: DB) -> dict:
    require_permission(user, session, "PROPERTY_VIEW")
    row = session.scalar(select(Property).options(joinedload(Property.parcels), joinedload(Property.conflicts)).where(Property.parcel_id == parcel_id.upper()))
    if not row:
        raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, department_key(user))
    audit(session, user, "VIEW", "PROPERTY", row.parcel_id)
    session.commit()
    match = session.scalar(select(AIMatch).where(AIMatch.property_id == row.id).order_by(AIMatch.created_at.desc()))
    return {"success": True, "data": {"property": property_response(row), "parcel": {"boundary": row.parcels[0].boundary if row.parcels else None, "centroid": row.parcels[0].centroid if row.parcels else None, "crs": row.parcels[0].crs if row.parcels else None}, "ai": {"match_score": match.match_score, "confidence_level": match.confidence_level, "explanation": match.explanation} if match else None, "conflicts": [{"id": str(item.id), "type": item.conflict_type, "severity": item.severity, "description": item.description, "status": item.status} for item in row.conflicts], "verification": {"status": row.verification_status}, "audit": []}}


@router.put("/properties/{parcel_id}")
def officer_edit(parcel_id: str, request: EditRequest, user: Officer, session: DB) -> dict:
    require_permission(user, session, "PROPERTY_EDIT")
    require_department(user, {"DISTRICT_ADMIN", "SUPER_ADMIN", "DEPARTMENT_ADMIN", "REVENUE_OFFICER", "GIS_SURVEY_OFFICER", "PLANNING_OFFICER"})
    allowed = {"owner_name", "co_owner_name", "land_use", "address", "verification_status", "conflict_status", "zone"}
    if request.field_name not in allowed:
        raise HTTPException(403, "This role cannot edit that field")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row:
        raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, department_key(user))
    old = str(getattr(row, request.field_name))
    setattr(row, request.field_name, request.new_value)
    version = (session.scalar(select(func.max(RecordVersion.version_number)).where(RecordVersion.property_id == row.id)) or 0) + 1
    session.add(RecordVersion(property_id=row.id, field_name=request.field_name, old_value=old, new_value=request.new_value, changed_by=user.id, department=user.department, reason=request.reason, version_number=version))
    audit(session, user, "UPDATE", "PROPERTY", row.parcel_id, request.reason, old, request.new_value)
    session.commit()
    return {"success": True, "data": {"parcel_id": row.parcel_id, "old_value": old, "new_value": request.new_value, "version_number": version}}


@router.get("/properties/{parcel_id}/history")
def officer_history(parcel_id: str, user: Officer, session: DB) -> dict:
    require_permission(user, session, "RECORD_VIEW")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, department_key(user))
    records = session.scalars(select(RecordVersion).where(RecordVersion.property_id == row.id).order_by(RecordVersion.version_number)).all()
    return {"success": True, "data": [{"field_name": item.field_name, "old_value": item.old_value, "new_value": item.new_value, "department": item.department, "reason": item.reason, "version_number": item.version_number, "created_at": item.created_at} for item in records]}


@router.post("/properties/{parcel_id}/verify")
def officer_verify(parcel_id: str, request: VerifyRequest, user: Officer, session: DB) -> dict:
    require_permission(user, session, "VERIFICATION_APPROVE")
    allowed = {"NEW", "AI_MATCHED", "REQUIRES_REVIEW", "UNDER_VERIFICATION", "VERIFIED", "REJECTED"}
    if request.status not in allowed: raise HTTPException(422, "Unsupported verification status")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, department_key(user))
    row.verification_status = request.status
    session.add(VerificationRecord(property_id=row.id, verified_by=user.id, department=user.department, status=request.status, reason=request.remarks))
    audit(session, user, "REJECT" if request.status == "REJECTED" else "VERIFY", "PROPERTY", row.parcel_id, request.remarks, None, request.status)
    session.commit()
    return {"success": True, "data": {"parcel_id": row.parcel_id, "status": request.status, "message": "Departmental verification status updated."}}


@router.post("/properties/{parcel_id}/flag")
def officer_flag_conflict(parcel_id: str, request: ConflictFlagRequest, user: Officer, session: DB) -> dict:
    require_permission(user, session, "CONFLICT_VIEW")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row:
        raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, department_key(user))
    conflict = Conflict(property_id=row.id, conflict_type=request.conflict_type, severity=request.severity, description=request.description, detected_by=str(user.id), status="OPEN")
    session.add(conflict)
    audit(session, user, "FLAG", "PROPERTY", row.parcel_id, request.description, new_value=request.severity)
    session.commit()
    return {"success": True, "data": {"conflict_id": str(conflict.id), "parcel_id": row.parcel_id, "status": conflict.status}}


@router.post("/ai/scan/{parcel_id}")
def officer_ai_scan(parcel_id: str, user: Officer, session: DB) -> dict:
    require_permission(user, session, "AI_SCAN")
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, department_key(user))
    left = {"parcel_id": row.parcel_id, "owner_name": row.owner_name, "address": row.address, "area_sq_m": row.area_sq_m, "land_use": row.land_use, "survey_number": row.survey_number, "khasra_number": row.khasra_number}
    result = match_records(left, left)
    record = AIMatch(property_id=row.id, match_score=result["match_score"], match_probability=result["match_probability"], confidence_level=result["confidence_level"], status="MATCH" if result["match_score"] >= 85 else "REQUIRES_REVIEW", matching_factors=result["matching_factors"], explanation=result["explanation"])
    session.add(record); audit(session, user, "AI_SCAN", "PROPERTY", row.parcel_id); session.commit()
    return {"success": True, "data": {"parcel_id": row.parcel_id, **result, "recommendation": "Manual verification required.", "disclaimer": "AI-assisted candidate match; no legal ownership decision is made."}}


@router.get("/gis/parcel/{parcel_id}")
def officer_gis_parcel(parcel_id: str, user: Officer, session: DB) -> dict:
    row = session.scalar(select(Property).options(joinedload(Property.parcels)).where(Property.parcel_id == parcel_id.upper()))
    if not row: raise HTTPException(404, "Property was not found.")
    require_department_access(user, "gis")
    require_permission(user, session, "GIS_VIEW")
    require_assigned_property(user, session, row, "gis")
    parcel = row.parcels[0] if row.parcels else None
    return {"success": True, "data": {"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude, "geometry": parcel.boundary if parcel else None, "centroid": parcel.centroid if parcel else None, "crs": parcel.crs if parcel else None}}


@router.get("/gis/viewport")
def officer_gis_viewport(north: float, south: float, east: float, west: float, user: Officer, session: DB) -> dict:
    require_department_access(user, "gis")
    require_permission(user, session, "GIS_VIEW")
    rows = session.scalars(select(Property).where(Property.id.in_(assigned_property_ids(user, "gis")), Property.latitude.between(south, north), Property.longitude.between(west, east)).limit(500)).all()
    return {"success": True, "data": [{"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude} for row in rows]}


@router.get("/gis/layers")
def officer_gis_layers(user: Officer, session: DB) -> dict:
    require_department_access(user, "gis")
    require_permission(user, session, "GIS_VIEW")
    from models.core import MapLayer
    rows = session.scalars(select(MapLayer).where(MapLayer.is_active.is_(True))).all()
    return {"success": True, "data": [{"name": row.name, "layer_type": row.layer_type, "provider": row.provider, "tile_url": row.tile_url, "attribution": row.attribution} for row in rows]}


@router.get("/gis/nearby")
def officer_gis_nearby(latitude: float, longitude: float, radius: float = 1000, user: Officer = None, session: DB = None) -> dict:
    require_department_access(user, "gis")
    require_permission(user, session, "GIS_VIEW")
    rows = session.scalars(select(Property).where(Property.id.in_(assigned_property_ids(user, "gis")), Property.latitude.between(latitude - radius / 111320, latitude + radius / 111320), Property.longitude.between(longitude - radius / 111320, longitude + radius / 111320)).limit(500)).all()
    return {"success": True, "data": [{"parcel_id": row.parcel_id, "owner_name": row.owner_name, "latitude": row.latitude, "longitude": row.longitude} for row in rows]}


@router.post("/gis/analyze")
def officer_gis_analyze(payload: dict, user: Officer, session: DB) -> dict:
    require_department_access(user, "gis")
    require_permission(user, session, "GIS_ANALYZE")
    parcel_id = str(payload.get("parcel_id", "")).upper()
    row = session.scalar(select(Property).where(Property.parcel_id == parcel_id))
    if not row: raise HTTPException(404, "Property was not found.")
    require_assigned_property(user, session, row, "gis")
    audit(session, user, "GIS_ANALYZE", "PROPERTY", parcel_id); session.commit()
    return {"success": True, "data": {"parcel_id": parcel_id, "area_sq_m": row.area_sq_m, "boundary_status": "AVAILABLE" if row.parcels else "UNAVAILABLE", "message": "Spatial comparison completed."}}


@router.post("/gis/upload")
async def officer_gis_upload(file: UploadFile = File(...), user: Officer = None, session: DB = None) -> dict:
    require_department_access(user, "gis")
    require_permission(user, session, "GIS_EDIT")
    if not (file.filename or "").lower().endswith((".geojson", ".json")):
        raise HTTPException(400, "GIS upload requires GeoJSON")
    content = await file.read()
    if len(content) > 25 * 1024 * 1024: raise HTTPException(413, "GIS upload exceeds 25 MB")
    audit(session, user, "UPLOAD", "GIS_DATASET", file.filename or "upload"); session.commit()
    return {"success": True, "data": {"filename": file.filename, "bytes": len(content), "status": "UPLOADED"}}


@router.get("/conflicts")
def officer_conflicts(user: Officer, session: DB) -> dict:
    require_permission(user, session, "CONFLICT_VIEW")
    scope = assigned_property_ids(user, department_key(user))
    rows = session.scalars(select(Conflict).where(Conflict.property_id.in_(scope)).order_by(Conflict.created_at.desc()).limit(500)).all()
    return {"success": True, "data": [{"id": str(row.id), "property_id": str(row.property_id), "conflict_type": row.conflict_type, "severity": row.severity, "description": row.description, "status": row.status} for row in rows]}


@router.post("/conflicts/{conflict_id}/resolve")
def officer_resolve_conflict(conflict_id: str, payload: dict, user: Officer, session: DB) -> dict:
    require_permission(user, session, "CONFLICT_RESOLVE")
    row = session.get(Conflict, conflict_id)
    if not row: raise HTTPException(404, "Conflict was not found.")
    property_row = session.get(Property, row.property_id)
    require_assigned_property(user, session, property_row, department_key(user))
    row.status = str(payload.get("status", "RESOLVED")); row.resolution = str(payload.get("resolution", "Officer review completed.")); row.resolved_by = user.id; row.resolved_at = datetime.now(timezone.utc)
    audit(session, user, "RESOLVE_CONFLICT", "CONFLICT", conflict_id, row.resolution); session.commit()
    return {"success": True, "data": {"id": conflict_id, "status": row.status, "resolution": row.resolution}}


@router.get("/audit")
def officer_audit(user: Officer, session: DB) -> dict:
    require_permission(user, session, "AUDIT_VIEW")
    rows = session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)).all()
    return {"success": True, "data": [{"action": row.action, "entity_type": row.entity_type, "entity_id": row.entity_id, "department": row.department, "reason": row.reason, "created_at": row.created_at} for row in rows]}


@router.post("/datasets/upload")
async def officer_dataset_upload(file: UploadFile = File(...), user: Officer = None, session: DB = None) -> dict:
    require_permission(user, session, "RECORD_UPLOAD")
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
    require_permission(user, session, "REPORT_EXPORT")
    record = Report(report_type=report_type, generated_by=user.id, status="READY")
    session.add(record); audit(session, user, "EXPORT", "REPORT", str(record.id)); session.commit()
    return {"success": True, "data": {"id": str(record.id), "report_type": report_type, "status": record.status}}


@router.get("/reports")
def reports(user: Officer, session: DB) -> dict:
    require_permission(user, session, "REPORT_VIEW")
    statement = select(Report).order_by(Report.created_at.desc()).limit(100)
    if user.role.name not in {"DISTRICT_ADMIN", "SUPER_ADMIN"}:
        statement = select(Report).join(User, User.id == Report.generated_by).where(func.lower(User.department) == (user.department or "").lower()).order_by(Report.created_at.desc()).limit(100)
    rows = session.scalars(statement).all()
    return {"success": True, "data": [{"id": str(row.id), "report_type": row.report_type, "status": row.status, "created_at": row.created_at} for row in rows]}


@router.get("/admin/officers")
def department_admin_officers(user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    officers = session.scalars(select(User).options(joinedload(User.role)).where(User.department.ilike(user.department), User.role.has(Role.name != "CITIZEN")).order_by(User.name)).all()
    return {"success": True, "data": [{"officer_id": str(item.id), "name": item.name, "email": item.email, "role": item.role.name, "department": department, "designation": item.designation, "is_active": item.is_active, "last_login": item.last_login} for item in officers]}


@router.post("/admin/officers")
def department_admin_create_officer(request: OfficerCreateRequest, user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    role_by_department = {"municipal": "MUNICIPAL_OFFICER", "registration": "REGISTRATION_OFFICER", "revenue": "REVENUE_OFFICER", "electricity": "ELECTRICITY_OFFICER", "property_tax": "PROPERTY_TAX_OFFICER", "gis": "GIS_SURVEY_OFFICER", "planning": "PLANNING_OFFICER"}
    role_name = role_by_department[department]
    if session.scalar(select(User.id).where(User.email == request.email.lower())):
        raise HTTPException(409, "An account already uses this email")
    role = session.scalar(select(Role).where(Role.name == role_name))
    officer_user = User(name=request.name, email=request.email.lower(), password_hash=hash_password(request.password), role_id=role.id, department=user.department, designation=request.designation or role_name.replace("_", " ").title(), is_active=True, is_verified=True)
    session.add(officer_user)
    session.flush()
    audit(session, user, "CREATE", "OFFICER", str(officer_user.id), f"Created {department} officer")
    session.commit()
    return {"success": True, "data": {"officer_id": str(officer_user.id), "name": officer_user.name, "email": officer_user.email, "role": role_name, "department": department, "designation": officer_user.designation, "is_active": True}}


@router.patch("/admin/officers/{officer_id}/active")
def department_admin_set_officer_active(officer_id: str, request: ActiveStatusRequest, user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    target = session.scalar(select(User).options(joinedload(User.role)).where(User.id == officer_id))
    if not target or department_key(target) != department or target.id == user.id:
        raise HTTPException(404, "Officer was not found in this department")
    target.is_active = request.is_active
    audit(session, user, "UPDATE", "OFFICER", str(target.id), "Officer activation status changed", new_value=str(request.is_active))
    session.commit()
    return {"success": True, "data": {"officer_id": str(target.id), "is_active": target.is_active}}


@router.get("/admin/assignments")
def department_admin_assignments(user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    rows = session.execute(select(OfficerAssignment, User, Property).join(User, User.id == OfficerAssignment.officer_id).join(Property, Property.id == OfficerAssignment.property_id).where(OfficerAssignment.department == department).order_by(OfficerAssignment.created_at.desc())).all()
    return {"success": True, "data": [{"assignment_id": str(assignment.id), "officer_id": str(officer.id), "officer_name": officer.name, "property_id": property_row.property_id or property_row.parcel_id, "parcel_id": property_row.parcel_id, "is_active": assignment.is_active, "created_at": assignment.created_at} for assignment, officer, property_row in rows]}


@router.post("/admin/assignments")
def department_admin_assign_record(request: AssignmentRequest, user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    target = session.scalar(select(User).options(joinedload(User.role)).where(User.id == request.officer_id, User.is_active.is_(True)))
    if not target or department_key(target) != department or target.role.name == "DEPARTMENT_ADMIN":
        raise HTTPException(403, "Officer must be active and belong to this department")
    property_row = session.scalar(select(Property).where(or_(Property.property_id == request.property_id, Property.parcel_id == request.property_id.upper())))
    if not property_row:
        raise HTTPException(404, "Property was not found")
    if request.from_officer_id:
        previous = session.scalar(select(OfficerAssignment).where(OfficerAssignment.officer_id == request.from_officer_id, OfficerAssignment.department == department, OfficerAssignment.property_id == property_row.id, OfficerAssignment.is_active.is_(True)))
        if not previous:
            raise HTTPException(404, "Existing assignment was not found")
        previous.is_active = False
        audit(session, user, "REASSIGN", "PROPERTY", property_row.parcel_id, "Record reassigned", old_value=request.from_officer_id, new_value=request.officer_id)
    assignment = session.scalar(select(OfficerAssignment).where(OfficerAssignment.officer_id == target.id, OfficerAssignment.department == department, OfficerAssignment.property_id == property_row.id))
    if assignment:
        assignment.is_active = True
    else:
        assignment = OfficerAssignment(officer_id=target.id, department=department, property_id=property_row.id, assigned_by=user.id)
        session.add(assignment)
    audit(session, user, "ASSIGN", "PROPERTY", property_row.parcel_id, "Record assigned", new_value=str(target.id))
    session.commit()
    return {"success": True, "data": {"assignment_id": str(assignment.id), "officer_id": str(target.id), "department": department, "property_id": property_row.property_id or property_row.parcel_id}}


@router.get("/admin/stats")
def department_admin_stats(user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    officer_count = session.scalar(select(func.count()).select_from(User).where(User.department.ilike(user.department), User.role.has(Role.name != "CITIZEN"))) or 0
    assignment_count = session.scalar(select(func.count()).select_from(OfficerAssignment).where(OfficerAssignment.department == department, OfficerAssignment.is_active.is_(True))) or 0
    return {"success": True, "data": {"department": department, "officers": officer_count, "active_assignments": assignment_count}}


@router.get("/admin/activity")
def department_admin_activity(user: Officer, session: DB) -> dict:
    department = require_department_admin(user, session)
    rows = session.scalars(select(AuditLog).where(func.lower(AuditLog.department) == (user.department or "").lower()).order_by(AuditLog.created_at.desc()).limit(250)).all()
    return {"success": True, "data": [{"officer_id": str(row.user_id) if row.user_id else None, "action": row.action, "record_id": row.entity_id, "reason": row.reason, "created_at": row.created_at} for row in rows]}
