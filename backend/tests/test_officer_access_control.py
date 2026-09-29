from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from database.session import SessionLocal
from main import app
from models.core import AuditLog, Role, User
from models.officer import OfficerAssignment
from security import hash_password

DEMO_PASSWORD = "BhoomiSyncDemo!2026"


def login(client: TestClient, email: str, password: str = DEMO_PASSWORD) -> str:
    response = client.post("/api/officer/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["data"]["access_token"]


def test_officer_login_and_department_scope():
    with TestClient(app) as client:
        assert client.post("/api/officer/auth/login", json={"email": "municipal.demo@bhoomisync.local", "password": "wrong"}).status_code == 401

        token = login(client, "municipal.demo@bhoomisync.local")
        headers = {"Authorization": f"Bearer {token}"}
        profile = client.get("/api/officer/me", headers=headers)
        assert profile.status_code == 200
        assert profile.json()["data"]["department_key"] == "municipal"
        assert profile.json()["data"]["assigned_record_count"] > 0
        assert "PROPERTY_VIEW" in profile.json()["data"]["permissions"]
        for email, department in [
            ("municipal.demo@bhoomisync.local", "municipal"),
            ("registration.demo@bhoomisync.local", "registration"),
            ("revenue.demo@bhoomisync.local", "revenue"),
            ("electricity.demo@bhoomisync.local", "electricity"),
            ("propertytax.demo@bhoomisync.local", "property_tax"),
            ("gis.demo@bhoomisync.local", "gis"),
            ("planning.demo@bhoomisync.local", "planning"),
        ]:
            login_token = login(client, email)
            identity = client.get("/api/officer/me", headers={"Authorization": f"Bearer {login_token}"})
            assert identity.json()["data"]["department_key"] == department
        assert client.get("/api/officer/departments/municipal", headers=headers).status_code == 200
        assert client.get("/api/officer/departments/revenue", headers=headers).status_code == 403
        unified = client.get("/api/officer/property/P1001", headers=headers)
        assert unified.status_code == 200
        assert set(unified.json()["data"]["departments"]) == {"municipal"}
        assert unified.json()["data"]["departments"]["municipal"]["assigned_officer"] == "Municipal Officer"
        assert client.get("/api/officer/gis/layers", headers=headers).status_code == 403
        assert client.get("/api/officer/satellite/history/P1001", headers=headers).status_code == 403

        gis_token = login(client, "gis.demo@bhoomisync.local")
        gis_headers = {"Authorization": f"Bearer {gis_token}"}
        assert client.get("/api/officer/gis/layers", headers=gis_headers).status_code == 200
        assert client.get("/api/officer/satellite/history/P1001", headers=gis_headers).status_code == 200


def test_officer_sees_only_individually_assigned_properties():
    with TestClient(app) as client:
        session = SessionLocal()
        email = f"unassigned-{uuid4()}@bhoomisync.local"
        user_id = None
        try:
            role = session.scalar(select(Role).where(Role.name == "MUNICIPAL_OFFICER"))
            user = User(name="Unassigned Test Officer", email=email, password_hash=hash_password("UnassignedTest!2026"), role_id=role.id, department="Municipal", is_active=True, is_verified=True)
            session.add(user)
            session.commit()
            user_id = user.id

            token = login(client, email, "UnassignedTest!2026")
            headers = {"Authorization": f"Bearer {token}"}
            summary = client.get("/api/officer/departments/municipal", headers=headers)
            assert summary.status_code == 200
            assert summary.json()["data"]["stats"]["total_records"] == 0
            assert client.get("/api/officer/properties/P1001", headers=headers).status_code == 403
        finally:
            if user_id:
                session.query(AuditLog).filter(AuditLog.user_id == user_id).delete()
                session.query(User).filter(User.id == user_id).delete()
                session.commit()
            session.close()


def test_department_admin_is_limited_to_own_department():
    email = f"created-{uuid4()}@bhoomisync.local"
    officer_id = None
    session = SessionLocal()
    with TestClient(app) as client:
        try:
            token = login(client, "municipal.admin.demo@bhoomisync.local")
            headers = {"Authorization": f"Bearer {token}"}
            assert client.get("/api/officer/admin/officers", headers=headers).status_code == 200
            assert client.get("/api/officer/admin/assignments", headers=headers).status_code == 200
            assert client.get("/api/officer/departments/revenue", headers=headers).status_code == 403
            assert client.get("/api/officer/admin/stats", headers=headers).json()["data"]["department"] == "municipal"

            created = client.post("/api/officer/admin/officers", headers=headers, json={"name": "Created Test Officer", "email": email, "password": "CreatedOfficer!2026", "designation": "Field Officer"})
            assert created.status_code == 200
            officer_id = created.json()["data"]["officer_id"]
            assignment = client.post("/api/officer/admin/assignments", headers=headers, json={"officer_id": officer_id, "property_id": "P1001"})
            assert assignment.status_code == 200
            token = login(client, email, "CreatedOfficer!2026")
            profile = client.get("/api/officer/me", headers={"Authorization": f"Bearer {token}"})
            assert profile.json()["data"]["assigned_record_count"] == 1
        finally:
            if officer_id:
                session.query(OfficerAssignment).filter(OfficerAssignment.officer_id == officer_id).delete(synchronize_session=False)
                session.query(AuditLog).filter(AuditLog.user_id == officer_id).delete(synchronize_session=False)
                session.query(User).filter(User.id == officer_id).delete(synchronize_session=False)
                session.commit()
            session.close()
