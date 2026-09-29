from gis.geometry import validate_geojson


def validate_boundary(geometry: dict) -> dict:
    return validate_geojson(geometry)
