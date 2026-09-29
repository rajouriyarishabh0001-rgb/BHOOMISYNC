from __future__ import annotations

from math import cos, pi, radians, sqrt


def approximate_distance_meters(latitude: float, longitude: float, other_latitude: float, other_longitude: float) -> float:
    lat_distance = (other_latitude - latitude) * 111_320
    lon_distance = (other_longitude - longitude) * 111_320 * cos(radians(latitude))
    return sqrt(lat_distance ** 2 + lon_distance ** 2)
