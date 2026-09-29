from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "gis"

REQUIRED_FILES = [
    "gis_parcels.geojson",
    "gis_revenue.geojson",
    "gis_municipal.geojson",
    "gis_planning.geojson",
    "gis_conflicts.geojson",
    "gis_ai_boundaries.geojson",
    "satellite_observations.json",
]


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def is_valid_geometry(value):
    if not isinstance(value, dict):
        return False
    if value.get("type") != "Polygon":
        return False
    coords = value.get("coordinates")
    if not isinstance(coords, list) or len(coords) == 0:
        return False
    ring = coords[0]
    if len(ring) < 5:
        return False
    return all(len(point) == 2 for point in ring)


def validate_feature_collection(name: str):
    data = load_json(DATA_DIR / name)
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{name} is not a GeoJSON FeatureCollection")
    features = data.get("features")
    if not isinstance(features, list):
        raise ValueError(f"{name} features missing")
    if len(features) == 0:
        raise ValueError(f"{name} has no features")

    for feature in features:
        if feature.get("type") != "Feature":
            raise ValueError(f"{name} contains non-feature items")
        props = feature.get("properties")
        if not isinstance(props, dict):
            raise ValueError(f"{name} contains a feature without properties")
        geometry = feature.get("geometry")
        if not is_valid_geometry(geometry):
            raise ValueError(f"{name} contains invalid geometry")

    return len(features)


def validate_satellite_observations():
    data = load_json(DATA_DIR / "satellite_observations.json")
    if not isinstance(data, list):
        raise ValueError("satellite_observations.json must be a JSON array")
    if len(data) == 0:
        raise ValueError("satellite_observations.json is empty")
    for item in data:
        if not isinstance(item.get("property_id"), str):
            raise ValueError("satellite observation missing property_id")
    return len(data)


if __name__ == "__main__":
    missing = [file for file in REQUIRED_FILES if not (DATA_DIR / file).exists()]
    if missing:
        raise SystemExit(f"Missing required files: {missing}")

    results = {}
    for file in REQUIRED_FILES[:-1]:
        results[file] = validate_feature_collection(file)
    results["satellite_observations.json"] = validate_satellite_observations()

    print(json.dumps(results, indent=2))
