from __future__ import annotations

import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
GIS_DIR = DATA_DIR / "gis"
SEED = 20260910
TOTAL_PARCELS = 1000
DISCLAIMER = "SYNTHETIC DEMO GIS DATA — NOT AN OFFICIAL CADASTRAL MAP"
CRS = "EPSG:4326"
LAND_USES = ["Residential", "Commercial", "Industrial", "Institutional", "Agricultural", "Mixed Use", "Vacant Land", "Public/Semi-Public"]
CLUSTER_TYPES = [
    "Residential",
    "Commercial",
    "Industrial",
    "Institutional",
    "Agricultural",
    "Mixed Use",
    "Vacant Land",
    "Public/Semi-Public",
    "Residential",
    "Commercial",
    "Mixed Use",
    "Residential",
    "Institutional",
    "Agricultural",
    "Vacant Land",
    "Public/Semi-Public",
    "Commercial",
    "Residential",
    "Industrial",
    "Institutional",
]
VILLAGES = ["Vidisha Urban", "Sanchi Road", "Betwa Nagar", "Ganj Basoda Road", "Civil Lines Extension", "Kachhi Khedi", "Madhav Nagar", "Raisen Link"]


def meters_to_lat(meters: float) -> float:
    return meters / 110_540


def meters_to_lon(meters: float, latitude: float) -> float:
    return meters / (111_320 * math.cos(math.radians(latitude)))


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def polygon_from_center(center_lon: float, center_lat: float, width_m: float, height_m: float, rng: random.Random, irregular: bool = False):
    half_w = width_m / 2
    half_h = height_m / 2

    base_points = [
        (-0.90 * half_w, -0.85 * half_h),
        (0.95 * half_w, -0.88 * half_h),
        (1.10 * half_w, -0.15 * half_h),
        (0.82 * half_w, 0.92 * half_h),
        (0.06 * half_w, 1.10 * half_h),
        (-1.05 * half_w, 0.40 * half_h),
        (-1.12 * half_w, -0.18 * half_h),
    ]

    if irregular:
        points = []
        for index, (x, y) in enumerate(base_points):
            jitter_x = rng.uniform(-0.10 * width_m, 0.10 * width_m)
            jitter_y = rng.uniform(-0.12 * height_m, 0.12 * height_m)
            points.append((x + jitter_x, y + jitter_y))
    else:
        points = []
        for index, (x, y) in enumerate(base_points):
            jitter_x = rng.uniform(-0.05 * width_m, 0.05 * width_m)
            jitter_y = rng.uniform(-0.05 * height_m, 0.05 * height_m)
            points.append((x + jitter_x, y + jitter_y))

    ring = []
    for x_m, y_m in points:
        lon = center_lon + meters_to_lon(x_m, center_lat)
        lat = center_lat + meters_to_lat(y_m)
        ring.append([round(lon, 6), round(lat, 6)])

    ring.append(ring[0])
    return {"type": "Polygon", "coordinates": [ring]}


def area_range(land_use: str):
    if land_use == "Residential":
        return (80, 800)
    if land_use == "Commercial":
        return (100, 2000)
    if land_use == "Industrial":
        return (500, 10000)
    if land_use == "Institutional":
        return (500, 15000)
    if land_use == "Agricultural":
        return (1000, 50000)
    if land_use == "Vacant Land":
        return (100, 5000)
    if land_use == "Mixed Use":
        return (300, 3000)
    return (150, 6000)


def parcel_dimensions(land_use: str, rng: random.Random):
    if land_use == "Residential":
        width_m = rng.uniform(18, 32)
        height_m = rng.uniform(22, 36)
    elif land_use == "Commercial":
        width_m = rng.uniform(28, 46)
        height_m = rng.uniform(20, 42)
    elif land_use == "Industrial":
        width_m = rng.uniform(42, 72)
        height_m = rng.uniform(34, 60)
    elif land_use == "Institutional":
        width_m = rng.uniform(35, 90)
        height_m = rng.uniform(30, 75)
    elif land_use == "Agricultural":
        width_m = rng.uniform(65, 120)
        height_m = rng.uniform(60, 130)
    elif land_use == "Vacant Land":
        width_m = rng.uniform(24, 60)
        height_m = rng.uniform(18, 50)
    elif land_use == "Mixed Use":
        width_m = rng.uniform(26, 48)
        height_m = rng.uniform(24, 44)
    else:
        width_m = rng.uniform(20, 55)
        height_m = rng.uniform(22, 48)
    return width_m, height_m


def derive_source_geometry(parcel: dict, source: str, rng: random.Random):
    if source == "Revenue GIS":
        return parcel["geometry"]
    if source == "Municipal GIS":
        center_lon = parcel["longitude"]
        center_lat = parcel["latitude"]
        width_m = parcel["_meta"]["width_m"] * rng.uniform(1.01, 1.03)
        height_m = parcel["_meta"]["height_m"] * rng.uniform(1.01, 1.04)
        return polygon_from_center(center_lon, center_lat, width_m, height_m, rng, irregular=True)
    if source == "Planning GIS":
        center_lon = parcel["longitude"] + rng.uniform(-0.00018, 0.00018)
        center_lat = parcel["latitude"] + rng.uniform(-0.00014, 0.00014)
        width_m = parcel["_meta"]["width_m"] * rng.uniform(1.03, 1.08)
        height_m = parcel["_meta"]["height_m"] * rng.uniform(1.02, 1.06)
        return polygon_from_center(center_lon, center_lat, width_m, height_m, rng, irregular=True)
    if source == "Survey GIS":
        center_lon = parcel["longitude"] + rng.uniform(-0.00008, 0.00008)
        center_lat = parcel["latitude"] + rng.uniform(-0.00006, 0.00006)
        width_m = parcel["_meta"]["width_m"] * rng.uniform(0.99, 1.02)
        height_m = parcel["_meta"]["height_m"] * rng.uniform(0.99, 1.02)
        return polygon_from_center(center_lon, center_lat, width_m, height_m, rng, irregular=False)
    center_lon = parcel["longitude"] + rng.uniform(-0.00020, 0.00020)
    center_lat = parcel["latitude"] + rng.uniform(-0.00016, 0.00016)
    width_m = parcel["_meta"]["width_m"] * rng.uniform(1.04, 1.12)
    height_m = parcel["_meta"]["height_m"] * rng.uniform(1.04, 1.10)
    return polygon_from_center(center_lon, center_lat, width_m, height_m, rng, irregular=True)


def build_parcels(rng: random.Random):
    parcels = []
    for index in range(TOTAL_PARCELS):
        parcel_number = index + 1001
        parcel_id = f"P{parcel_number}"
        cluster_index = index // 50
        cluster_row = (index % 50) // 5
        cluster_col = (index % 50) % 5

        cluster_lon_base = 77.785 + (cluster_index % 5) * 0.013
        cluster_lat_base = 23.505 + (cluster_index // 5) * 0.0105

        lon_offset = (cluster_col - 2) * 0.00135 + rng.uniform(-0.00018, 0.00018)
        lat_offset = (cluster_row - 4) * 0.0012 + rng.uniform(-0.00014, 0.00014)

        center_lon = cluster_lon_base + lon_offset
        center_lat = cluster_lat_base + lat_offset

        land_use = CLUSTER_TYPES[cluster_index % len(CLUSTER_TYPES)]
        if index % 17 == 0:
            land_use = LAND_USES[(index + 3) % len(LAND_USES)]

        area_min, area_max = area_range(land_use)
        area_sq_m = round(rng.uniform(area_min, area_max), 2)
        width_m, height_m = parcel_dimensions(land_use, rng)
        width_m = clamp(width_m, 12, 110)
        height_m = clamp(height_m, 12, 140)

        polygon = polygon_from_center(center_lon, center_lat, width_m, height_m, rng, irregular=land_use in {"Agricultural", "Vacant Land", "Mixed Use"})
        ward = (cluster_index % 12) + 1

        properties = {
            "property_id": parcel_id,
            "parcel_id": parcel_id,
            "survey_number": f"SUR-{parcel_number:05d}",
            "khasra_number": f"KHA-{parcel_number:05d}",
            "ward": ward,
            "village": VILLAGES[cluster_index % len(VILLAGES)],
            "tehsil": "Vidisha",
            "district": "Vidisha",
            "land_use": land_use,
            "area_sq_m": area_sq_m,
            "latitude": round(center_lat, 6),
            "longitude": round(center_lon, 6),
            "geometry": polygon,
            "crs": CRS,
            "data_disclaimer": DISCLAIMER,
            "property_type": land_use,
        }

        quality_bucket = "BOUNDARY_MATCH" if index < 700 else "MINOR_BOUNDARY_VARIANCE" if index < 900 else "MAJOR_BOUNDARY_VARIANCE"

        if quality_bucket == "BOUNDARY_MATCH":
            gis_match_score = round(rng.uniform(0.93, 0.99), 2)
            geometry_similarity = round(rng.uniform(0.90, 0.99), 2)
            area_similarity = round(rng.uniform(0.95, 0.99), 2)
            centroid_distance_m = round(rng.uniform(0.3, 2.0), 2)
            overlap_percentage = round(rng.uniform(92, 99), 2)
            confidence_level = "HIGH"
            match_status = "MATCH"
        elif quality_bucket == "MINOR_BOUNDARY_VARIANCE":
            gis_match_score = round(rng.uniform(0.82, 0.92), 2)
            geometry_similarity = round(rng.uniform(0.78, 0.90), 2)
            area_similarity = round(rng.uniform(0.88, 0.96), 2)
            centroid_distance_m = round(rng.uniform(2.1, 8.0), 2)
            overlap_percentage = round(rng.uniform(78, 91), 2)
            confidence_level = "MEDIUM"
            match_status = "MATCH"
        else:
            gis_match_score = round(rng.uniform(0.65, 0.81), 2)
            geometry_similarity = round(rng.uniform(0.60, 0.78), 2)
            area_similarity = round(rng.uniform(0.70, 0.89), 2)
            centroid_distance_m = round(rng.uniform(8.1, 25.0), 2)
            overlap_percentage = round(rng.uniform(58, 77), 2)
            confidence_level = "LOW"
            match_status = "REQUIRES_REVIEW"

        properties.update(
            {
                "gis_match_score": gis_match_score,
                "geometry_similarity": geometry_similarity,
                "area_similarity": area_similarity,
                "centroid_distance_m": centroid_distance_m,
                "overlap_percentage": overlap_percentage,
                "confidence_level": confidence_level,
                "match_status": match_status,
                "gis_status": quality_bucket,
                "boundary_source": "Reference parcel boundary",
                "locality": f"Cluster {cluster_index + 1}",
                "_meta": {
                    "width_m": width_m,
                    "height_m": height_m,
                    "quality_bucket": quality_bucket,
                },
            }
        )
        parcels.append(properties)

    return parcels


def build_feature_collection(features):
    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "disclaimer": DISCLAIMER,
            "crs": CRS,
        },
    }


def feature_from_parcel(parcel: dict, source: str):
    feature = {
        "type": "Feature",
        "properties": {
            "property_id": parcel["property_id"],
            "parcel_id": parcel["parcel_id"],
            "survey_number": parcel["survey_number"],
            "khasra_number": parcel["khasra_number"],
            "ward": parcel["ward"],
            "village": parcel["village"],
            "tehsil": parcel["tehsil"],
            "district": parcel["district"],
            "land_use": parcel["land_use"],
            "area_sq_m": parcel["area_sq_m"],
            "latitude": parcel["latitude"],
            "longitude": parcel["longitude"],
            "gis_status": parcel["gis_status"],
            "gis_match_score": parcel["gis_match_score"],
            "geometry_similarity": parcel["geometry_similarity"],
            "area_similarity": parcel["area_similarity"],
            "centroid_distance_m": parcel["centroid_distance_m"],
            "overlap_percentage": parcel["overlap_percentage"],
            "confidence_level": parcel["confidence_level"],
            "match_status": parcel["match_status"],
            "boundary_source": source,
            "data_disclaimer": DISCLAIMER,
            "property_type": parcel["property_type"],
        },
        "geometry": parcel["geometry"],
    }
    return feature


def generate_conflicts(parcels: list[dict], rng: random.Random):
    conflicts = []
    conflict_types = ["GIS_BOUNDARY_VARIANCE", "GIS_AREA_MISMATCH", "PARCEL_GEOMETRY_MISMATCH", "MISSING_GIS_RECORD", "DUPLICATE_GIS_RECORD"]
    conflict_count = 0

    for index, parcel in enumerate(parcels):
        base_conflict_type = conflict_types[index % len(conflict_types)]
        if index < 150:
            conflict_type = base_conflict_type
        else:
            conflict_type = conflict_types[(index + 1) % len(conflict_types)]

        if conflict_type == "GIS_BOUNDARY_VARIANCE":
            comparison_geometry = polygon_from_center(parcel["longitude"], parcel["latitude"], parcel["_meta"]["width_m"] * rng.uniform(1.02, 1.08), parcel["_meta"]["height_m"] * rng.uniform(1.02, 1.07), rng, irregular=True)
            area_difference_sq_m = round(abs(parcel["area_sq_m"] * 0.03), 2)
            overlap_percentage = round(rng.uniform(76, 89), 2)
            severity = "MEDIUM"
            explanation = "Synthetic boundary variance detected between source GIS layers; parcel remains in review for field verification."
        elif conflict_type == "GIS_AREA_MISMATCH":
            comparison_geometry = polygon_from_center(parcel["longitude"], parcel["latitude"], parcel["_meta"]["width_m"] * rng.uniform(0.90, 0.98), parcel["_meta"]["height_m"] * rng.uniform(0.90, 0.98), rng, irregular=False)
            area_difference_sq_m = round(abs(parcel["area_sq_m"] * rng.uniform(0.08, 0.22)), 2)
            overlap_percentage = round(rng.uniform(70, 84), 2)
            severity = "HIGH"
            explanation = "Synthetic area mismatch between GIS source layers and the reference parcel area."
        elif conflict_type == "PARCEL_GEOMETRY_MISMATCH":
            comparison_geometry = polygon_from_center(parcel["longitude"] + 0.0007, parcel["latitude"] - 0.0005, parcel["_meta"]["width_m"] * 1.08, parcel["_meta"]["height_m"] * 1.10, rng, irregular=True)
            area_difference_sq_m = round(abs(parcel["area_sq_m"] * rng.uniform(0.05, 0.18)), 2)
            overlap_percentage = round(rng.uniform(62, 78), 2)
            severity = "HIGH"
            explanation = "Synthetic geometry mismatch indicates different parcel boundary interpretations across layers."
        elif conflict_type == "MISSING_GIS_RECORD":
            comparison_geometry = polygon_from_center(parcel["longitude"], parcel["latitude"], parcel["_meta"]["width_m"] * 0.80, parcel["_meta"]["height_m"] * 0.80, rng, irregular=False)
            area_difference_sq_m = round(parcel["area_sq_m"] * 0.10, 2)
            overlap_percentage = 0
            severity = "LOW"
            explanation = "Synthetic missing GIS record is represented as an unlinked layer record requiring reconciliation."
        else:
            comparison_geometry = polygon_from_center(parcel["longitude"] + 0.00015, parcel["latitude"] + 0.00012, parcel["_meta"]["width_m"] * 1.02, parcel["_meta"]["height_m"] * 1.01, rng, irregular=False)
            area_difference_sq_m = round(abs(parcel["area_sq_m"] * rng.uniform(0.01, 0.06)), 2)
            overlap_percentage = round(rng.uniform(88, 96), 2)
            severity = "MEDIUM"
            explanation = "Synthetic duplicate GIS record exists in the demo layer and should be reviewed for harmonization."

        conflict_id = f"CONF-{index + 1:04d}"
        conflict = {
            "conflict_id": conflict_id,
            "property_id": parcel["property_id"],
            "parcel_id": parcel["parcel_id"],
            "conflict_type": conflict_type,
            "severity": severity,
            "source_geometry": parcel["geometry"],
            "comparison_geometry": comparison_geometry,
            "area_difference_sq_m": area_difference_sq_m,
            "overlap_percentage": overlap_percentage,
            "status": "OPEN",
            "explanation": explanation,
            "data_disclaimer": DISCLAIMER,
        }
        conflicts.append(conflict)
        conflict_count += 1

    return conflicts


def generate_ai_boundaries(parcels: list[dict], rng: random.Random):
    ai_boundaries = []
    for index, parcel in enumerate(parcels):
        if index % 10 != 0:
            continue
        width_m = parcel["_meta"]["width_m"] * rng.uniform(1.06, 1.16)
        height_m = parcel["_meta"]["height_m"] * rng.uniform(1.04, 1.14)
        ai_geometry = polygon_from_center(parcel["longitude"] + rng.uniform(-0.00025, 0.00025), parcel["latitude"] + rng.uniform(-0.00020, 0.00020), width_m, height_m, rng, irregular=True)
        ai_boundaries.append(
            {
                "type": "Feature",
                "properties": {
                    "property_id": parcel["property_id"],
                    "parcel_id": parcel["parcel_id"],
                    "reference_geometry": parcel["geometry"],
                    "ai_candidate_geometry": ai_geometry,
                    "geometry_similarity": round(rng.uniform(0.68, 0.88), 2),
                    "boundary_difference": round(rng.uniform(2.5, 12.0), 2),
                    "confidence": round(rng.uniform(0.60, 0.85), 2),
                    "explanation": "Synthetic AI candidate boundary for visual assistance only; it is not an official cadastral boundary.",
                    "data_disclaimer": DISCLAIMER,
                },
                "geometry": parcel["geometry"],
            }
        )
    return ai_boundaries


def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def write_geojson(path: Path, feature_collection):
    write_json(path, feature_collection)


def generate_satellite_observations(parcels: list[dict], rng: random.Random):
    observations = []
    for index, parcel in enumerate(parcels[:800]):
        built_up = round(rng.uniform(18, 76), 1)
        vegetation = round(rng.uniform(10, 55), 1)
        water = round(clamp(100 - built_up - vegetation, 2, 25), 1)
        observations.append(
            {
                "observation_id": f"SAT-{index + 1:04d}",
                "property_id": parcel["property_id"],
                "parcel_id": parcel["parcel_id"],
                "image_date": "2026-08-15",
                "provider": "Synthetic imagery simulator",
                "cloud_cover": round(rng.uniform(3, 28), 1),
                "built_up_percentage": built_up,
                "vegetation_percentage": vegetation,
                "water_percentage": water,
                "land_cover": "Built-up / Open" if built_up > 50 else "Vegetation / Open",
                "change_detected": index % 6 == 0,
                "change_confidence": round(rng.uniform(0.64, 0.90), 2),
                "analysis_summary": "Synthetic satellite-derived observation only; no real imagery was analyzed.",
                "data_disclaimer": DISCLAIMER,
            }
        )
    return observations


def generate():
    rng = random.Random(SEED)

    GIS_DIR.mkdir(parents=True, exist_ok=True)

    parcels = build_parcels(rng)
    conflicts = generate_conflicts(parcels, rng)
    ai_boundaries = generate_ai_boundaries(parcels, rng)
    satellite_observations = generate_satellite_observations(parcels, rng)

    primary_features = []
    revenue_features = []
    municipal_features = []
    planning_features = []

    for parcel in parcels:
        primary_features.append(feature_from_parcel(parcel, "Reference Parcel Boundary"))
        revenue_features.append(feature_from_parcel(parcel, "Revenue GIS"))
        municipal_features.append(feature_from_parcel(parcel, "Municipal GIS"))
        planning_features.append(feature_from_parcel(parcel, "Planning GIS"))

    revenue_features = [feature_from_parcel(parcel, "Revenue GIS") for parcel in parcels]
    municipal_features = [feature_from_parcel(parcel, "Municipal GIS") for parcel in parcels]
    planning_features = [feature_from_parcel(parcel, "Planning GIS") for parcel in parcels]

    for feature in municipal_features:
        feature["properties"]["gis_status"] = "MINOR_BOUNDARY_VARIANCE" if int(feature["properties"]["parcel_id"].split("P")[-1]) % 5 == 0 else feature["properties"]["gis_status"]

    for feature in planning_features:
        feature["properties"]["ward"] = int(feature["properties"]["ward"]) + 1
        feature["properties"]["land_use"] = "Mixed Use" if int(feature["properties"]["parcel_id"].split("P")[-1]) % 7 == 0 else feature["properties"]["land_use"]

    conflict_features = []
    for conflict in conflicts:
        conflict_features.append(
            {
                "type": "Feature",
                "properties": {
                    "conflict_id": conflict["conflict_id"],
                    "property_id": conflict["property_id"],
                    "parcel_id": conflict["parcel_id"],
                    "conflict_type": conflict["conflict_type"],
                    "severity": conflict["severity"],
                    "area_difference_sq_m": conflict["area_difference_sq_m"],
                    "overlap_percentage": conflict["overlap_percentage"],
                    "status": conflict["status"],
                    "explanation": conflict["explanation"],
                    "source_geometry": conflict["source_geometry"],
                    "comparison_geometry": conflict["comparison_geometry"],
                    "data_disclaimer": DISCLAIMER,
                },
                "geometry": conflict["source_geometry"],
            }
        )

    write_geojson(GIS_DIR / "gis_parcels.geojson", build_feature_collection(primary_features))
    write_geojson(GIS_DIR / "gis_revenue.geojson", build_feature_collection(revenue_features))
    write_geojson(GIS_DIR / "gis_municipal.geojson", build_feature_collection(municipal_features))
    write_geojson(GIS_DIR / "gis_planning.geojson", build_feature_collection(planning_features))
    write_geojson(GIS_DIR / "gis_conflicts.geojson", build_feature_collection(conflict_features))
    write_geojson(GIS_DIR / "gis_ai_boundaries.geojson", build_feature_collection(ai_boundaries))
    write_json(GIS_DIR / "satellite_observations.json", satellite_observations)

    counts = {
        "Total Parcels": TOTAL_PARCELS,
        "Valid Geometries": TOTAL_PARCELS,
        "Revenue GIS": len(revenue_features),
        "Municipal GIS": len(municipal_features),
        "Planning GIS": len(planning_features),
        "Boundary Matches": sum(1 for parcel in parcels if parcel["gis_status"] == "BOUNDARY_MATCH"),
        "Minor Variances": sum(1 for parcel in parcels if parcel["gis_status"] == "MINOR_BOUNDARY_VARIANCE"),
        "Major Variances": sum(1 for parcel in parcels if parcel["gis_status"] == "MAJOR_BOUNDARY_VARIANCE"),
        "GIS Conflicts": len(conflicts),
        "AI Candidate Boundaries": len(ai_boundaries),
        "Satellite Observations": len(satellite_observations),
    }

    return counts


if __name__ == "__main__":
    counts = generate()
    print(json.dumps(counts, indent=2))
