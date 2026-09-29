import sqlite3
import random
import json
from datetime import datetime

DB_PATH = "bhoomisync.db"

random.seed(42)

# ---------------------------------------------------------
# DEMO NAMES
# ---------------------------------------------------------

FIRST_NAMES = [
    "Rahul", "Suresh", "Amit", "Pooja", "Ravi",
    "Neha", "Ankit", "Priya", "Vikas", "Nisha",
    "Rohit", "Kavita", "Manish", "Sneha", "Deepak",
    "Anjali", "Arjun", "Simran", "Mohit", "Riya",
    "Karan", "Shivani", "Abhishek", "Payal", "Vivek"
]

LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Singh", "Jain",
    "Gupta", "Khan", "Joshi", "Yadav", "Mishra",
    "Saxena", "Tiwari", "Choudhary", "Mehta", "Agrawal",
    "Dubey", "Malviya", "Thakur", "Soni", "Rathore"
]

LAND_USES = [
    "Residential",
    "Commercial",
    "Mixed Use",
    "Agricultural",
    "Institutional"
]

PROPERTY_TYPES = [
    "Plot",
    "House",
    "Commercial Plot",
    "Apartment",
    "Agricultural Land"
]

VILLAGES = [
    "Vidisha",
    "Sanchi Road",
    "Baripura",
    "Khatamkheda",
    "Gulabganj",
    "Mukherjee Nagar",
    "Civil Lines"
]

STREETS = [
    "Main Road",
    "Station Road",
    "Sanchi Road",
    "Civil Lines",
    "College Road",
    "MG Road",
    "Ring Road"
]

# ---------------------------------------------------------
# DATABASE
# ---------------------------------------------------------

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ---------------------------------------------------------
# PERSON TABLE
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    name_normalized TEXT NOT NULL,
    father_or_guardian_name TEXT,
    address TEXT,
    village TEXT,
    ward INTEGER,
    tehsil TEXT,
    district TEXT,
    state TEXT,
    pincode TEXT,
    data_type TEXT DEFAULT 'SYNTHETIC_DEMO',
    created_at TEXT,
    updated_at TEXT
)
""")

# ---------------------------------------------------------
# PROPERTY TABLE
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcel_id TEXT UNIQUE NOT NULL,
    property_id TEXT UNIQUE NOT NULL,
    owner_name TEXT NOT NULL,
    survey_number TEXT,
    khasra_number TEXT,
    area_sq_m REAL,
    land_use TEXT,
    property_type TEXT,
    address TEXT,
    ward INTEGER,
    village TEXT,
    tehsil TEXT,
    district TEXT,
    state TEXT,
    pincode TEXT,
    latitude REAL,
    longitude REAL,
    verification_status TEXT,
    conflict_status TEXT,
    data_type TEXT DEFAULT 'SYNTHETIC_DEMO',
    created_at TEXT,
    updated_at TEXT
)
""")

# ---------------------------------------------------------
# PROPERTY OWNERS
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS property_owners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id TEXT NOT NULL,
    person_id TEXT NOT NULL,
    ownership_type TEXT NOT NULL,
    ownership_percentage REAL NOT NULL
)
""")

# ---------------------------------------------------------
# GIS TABLE
# ---------------------------------------------------------

cursor.execute("""
CREATE TABLE IF NOT EXISTS gis_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parcel_id TEXT UNIQUE NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    geometry TEXT NOT NULL,
    source_department TEXT,
    data_type TEXT DEFAULT 'SYNTHETIC_DEMO'
)
""")

# ---------------------------------------------------------
# CLEAR OLD DEMO DATA
# ---------------------------------------------------------

cursor.execute("DELETE FROM property_owners")
cursor.execute("DELETE FROM gis_records")
cursor.execute("DELETE FROM properties")
cursor.execute("DELETE FROM persons")

# ---------------------------------------------------------
# GENERATE 200 PEOPLE
# ---------------------------------------------------------

people = []

for i in range(1, 201):

    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)

    full_name = f"{first} {last}"

    father = (
        f"{random.choice(FIRST_NAMES)} "
        f"{random.choice(LAST_NAMES)}"
    )

    village = random.choice(VILLAGES)
    ward = random.randint(1, 15)

    address = (
        f"{random.choice(STREETS)}, "
        f"Ward {ward}, {village}"
    )

    person_id = f"PERSON-{i:03d}"

    created_at = datetime.now().isoformat()

    people.append({
        "person_id": person_id,
        "full_name": full_name,
        "father": father,
        "address": address,
        "village": village,
        "ward": ward
    })

    cursor.execute("""
        INSERT INTO persons (
            person_id,
            full_name,
            name_normalized,
            father_or_guardian_name,
            address,
            village,
            ward,
            tehsil,
            district,
            state,
            pincode,
            data_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        person_id,
        full_name,
        full_name.lower(),
        father,
        address,
        village,
        ward,
        "Vidisha",
        "Vidisha",
        "Madhya Pradesh",
        "464001",
        "SYNTHETIC_DEMO",
        created_at,
        created_at
    ))

# ---------------------------------------------------------
# GENERATE 250 PROPERTIES
# ---------------------------------------------------------

for i in range(1, 251):

    parcel_id = f"P{1000 + i}"
    property_id = f"PROP{1000 + i}"

    # Random owner
    person = random.choice(people)

    owner_name = person["full_name"]

    ward = person["ward"]
    village = person["village"]

    # Vidisha demo coordinates
    latitude = 23.5200 + random.uniform(-0.025, 0.025)
    longitude = 77.8050 + random.uniform(-0.025, 0.025)

    area = round(random.uniform(70, 1000), 2)

    land_use = random.choice(LAND_USES)
    property_type = random.choice(PROPERTY_TYPES)

    survey_number = f"SV-{1000 + i}"
    khasra_number = f"KH-{1000 + i}"

    address = person["address"]

    verification_status = random.choice([
        "VERIFIED",
        "REQUIRES_REVIEW",
        "PENDING"
    ])

    conflict_status = random.choices(
        ["NONE", "LOW", "MEDIUM"],
        weights=[75, 15, 10]
    )[0]

    now = datetime.now().isoformat()

    # -----------------------------
    # PROPERTY
    # -----------------------------

    cursor.execute("""
        INSERT INTO properties (
            parcel_id,
            property_id,
            owner_name,
            survey_number,
            khasra_number,
            area_sq_m,
            land_use,
            property_type,
            address,
            ward,
            village,
            tehsil,
            district,
            state,
            pincode,
            latitude,
            longitude,
            verification_status,
            conflict_status,
            data_type,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        parcel_id,
        property_id,
        owner_name,
        survey_number,
        khasra_number,
        area,
        land_use,
        property_type,
        address,
        ward,
        village,
        "Vidisha",
        "Vidisha",
        "Madhya Pradesh",
        "464001",
        latitude,
        longitude,
        verification_status,
        conflict_status,
        "SYNTHETIC_DEMO",
        now,
        now
    ))

    # -----------------------------
    # PROPERTY OWNER RELATION
    # -----------------------------

    cursor.execute("""
        INSERT INTO property_owners (
            property_id,
            person_id,
            ownership_type,
            ownership_percentage
        )
        VALUES (?, ?, ?, ?)
    """, (
        parcel_id,
        person["person_id"],
        "PRIMARY_OWNER",
        100
    ))

    # -----------------------------
    # CREATE PROPERTY BOUNDARY
    # -----------------------------

    size = random.uniform(0.00025, 0.00055)

    geometry = {
        "type": "Polygon",
        "coordinates": [[
            [
                longitude - size,
                latitude - size
            ],
            [
                longitude + size,
                latitude - size
            ],
            [
                longitude + size,
                latitude + size
            ],
            [
                longitude - size,
                latitude + size
            ],
            [
                longitude - size,
                latitude - size
            ]
        ]]
    }

    cursor.execute("""
        INSERT INTO gis_records (
            parcel_id,
            latitude,
            longitude,
            geometry,
            source_department,
            data_type
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        parcel_id,
        latitude,
        longitude,
        json.dumps(geometry),
        "DEMO_GIS",
        "SYNTHETIC_DEMO"
    ))

# ---------------------------------------------------------
# COMMIT
# ---------------------------------------------------------

conn.commit()

# ---------------------------------------------------------
# SHOW COUNTS
# ---------------------------------------------------------

person_count = cursor.execute(
    "SELECT COUNT(*) FROM persons"
).fetchone()[0]

property_count = cursor.execute(
    "SELECT COUNT(*) FROM properties"
).fetchone()[0]

gis_count = cursor.execute(
    "SELECT COUNT(*) FROM gis_records"
).fetchone()[0]

print()
print("======================================")
print(" BHOOMISYNC USER DEMO DATABASE")
print("======================================")
print(f"Persons       : {person_count}")
print(f"Properties    : {property_count}")
print(f"GIS Boundaries: {gis_count}")
print("======================================")
print("Data type: SYNTHETIC DEMO")
print("NOT OFFICIAL GOVERNMENT RECORDS")
print("======================================")

conn.close()