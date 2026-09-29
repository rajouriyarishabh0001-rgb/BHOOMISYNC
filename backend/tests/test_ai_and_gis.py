from ai.matcher import match_records
from gis.geometry import geometry_similarity, validate_geojson


def test_explainable_match_returns_factors():
    result = match_records(
        {"parcel_id": "P1001", "owner_name": "Rahul Sharma", "area_sq_m": 100, "land_use": "Residential"},
        {"parcel_id": "P1001", "owner_name": "R. Sharma", "area_sq_m": 101, "land_use": "Residential"},
    )
    assert result["match_score"] > 70
    assert "owner_similarity" in result["matching_factors"]
    assert result["explanation"]


def test_geojson_validation_and_similarity():
    polygon = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]}
    assert validate_geojson(polygon) == polygon
    assert geometry_similarity(polygon, polygon) == 1.0