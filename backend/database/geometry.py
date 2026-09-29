from __future__ import annotations

from typing import Any

from geoalchemy2 import Geometry
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import mapping, shape
from sqlalchemy.types import JSON, TypeDecorator


class PortableGeometry(TypeDecorator):
    """PostGIS geometry in production, GeoJSON JSON fallback for SQLite."""

    impl = JSON
    cache_ok = True

    def __init__(self, geometry_type: str, srid: int = 4326, *args, **kwargs):
        self.geometry_type = geometry_type
        self.srid = srid
        super().__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(Geometry(geometry_type=self.geometry_type, srid=self.srid, spatial_index=True))
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value: Any, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return from_shape(shape(value), srid=self.srid)
        return value

    def process_result_value(self, value: Any, dialect):
        if value is None or dialect.name != "postgresql":
            return value
        return mapping(to_shape(value))