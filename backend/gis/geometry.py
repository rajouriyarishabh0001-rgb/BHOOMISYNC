from __future__ import annotations

from typing import Any

from shapely.geometry import shape
from shapely.validation import explain_validity


def validate_geojson(geometry: dict[str, Any]) -> dict[str, Any]:
    candidate = shape(geometry)
    if candidate.is_empty or not candidate.is_valid:
        raise ValueError(f"Invalid geometry: {explain_validity(candidate)}")
    return geometry


def geometry_area(geometry: dict[str, Any]) -> float:
    return float(shape(geometry).area)


def geometry_similarity(left: dict[str, Any] | None, right: dict[str, Any] | None) -> float:
    if not left or not right:
        return 0.0
    first, second = shape(left), shape(right)
    union = first.union(second).area
    return round(first.intersection(second).area / union, 4) if union else 0.0
