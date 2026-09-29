# Syncbhoomi Synthetic Data Package

**SYNTHETIC DEMO DATA — NOT OFFICIAL GOVERNMENT RECORDS**

This package contains reproducible, fictional urban land records inspired by the Vidisha, Madhya Pradesh area. It does not represent any government department, real person, real address, real ownership, or real satellite analysis.

## Contents

- `persons.csv`: exactly 200 synthetic people, `PERSON-001` to `PERSON-200`
- `properties.csv`: exactly 1,000 properties, `P1001` to `P2000`
- `property_owners.csv`: one linked owner record for every property
- `revenue_records.csv`: 1,000 records
- `registration_records.csv`: 950 records
- `municipal_records.csv`: 980 records
- `property_tax_records.csv`: 940 records
- `gis_records.csv`: 1,000 valid GeoJSON parcel polygons
- `planning_records.csv`: 900 records
- `satellite_observations.csv`: 800 synthetic observations; no real imagery was analyzed
- `ai_matches.csv`: 1,000 explainable candidate matches
- `conflicts.csv`: 190 cross-source review conflicts
- `verification_records.csv`: 1,000 departmental/demo verification records
- `audit_logs.csv`: 300 synthetic audit events

Every row includes `data_type` with the value:

`SYNTHETIC DEMO DATA — NOT OFFICIAL GOVERNMENT RECORDS`

## Generate Again

From the repository root:

```powershell
cd backend
python scripts/generate_synthetic_data.py
python scripts/validate_synthetic_data.py
```

The generator uses deterministic seed `20260910`, so the same files are produced on every run.

## Load the Local SQLite Demo Register

This wrapper regenerates the CSV package and loads the existing legacy SQLite register used by the local MVP:

```powershell
cd backend
python scripts/seed_synthetic_data.py
```

The local database file is `backend/bhoomisync.db`. The normal application startup then imports the legacy register into the normalized SQLAlchemy tables when needed.

Run the application:

```powershell
cd backend
uvicorn main:app --reload --port 8000
```

## Data Relationships

All source rows link back to the same property through `property_id` and `parcel_id`. Survey and khasra numbers are also shared across source datasets. Records intentionally include clean matches, owner-name variations, missing departments, area and land-use mismatches, GIS boundary variance, duplicate/conflict signals, synthetic satellite changes, and review statuses.

`VERIFIED` means demo/departamental workflow verification only. It does not mean legally verified ownership.

## Validation

The validator checks:

- property ID range and person ID range
- expected source row counts
- duplicate identifiers
- missing property references
- synthetic-data markers
- closed Polygon GeoJSON structure
- source relationship integrity

No real personal identifiers are used. Phone values are reserved synthetic values in the `9000000xxx` range and emails use `example.test`.
