# BHOOMISYNC

Smart Land Records, One Unified View.

BHOOMISYNC is a local MVP demonstrating public land-information discovery and a separate officer intelligence workspace.

## Structure

- `backend/` FastAPI API, SQLite demo database, matching and GIS services
- `frontend/` React + TypeScript + Vite application

## Run backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m scripts.seed_demo_data
python -m scripts.seed_database
uvicorn main:app --reload --port 8000
```

The primary deployment target is PostgreSQL 15+ with PostGIS enabled. Set
`DATABASE_URL=postgresql+psycopg://...` in `backend/.env` and run
`alembic upgrade head`. Local development falls back to SQLite when the default
`.env` is used. The normalized SQLAlchemy schema is in `backend/models/`, while
the legacy SQLite routes remain available during migration.

The normalized API includes JWT authentication under `/api/auth`, RBAC role
records, `/api/maps/layers`, `/api/maps/config`, `/api/maps/viewport`,
`/api/properties/nearby`, `/api/location`, `/api/satellite/layers`, and
PostGIS-backed spatial queries when PostgreSQL is active.

## Run frontend

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The officer workspace uses demo role selection rather than real credentials.
