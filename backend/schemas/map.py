from typing import Any

from pydantic import BaseModel


class MapLayerResponse(BaseModel):
    id: str
    name: str
    name_hi: str | None
    layer_type: str
    provider: str
    tile_url: str | None
    attribution: str | None
    min_zoom: int
    max_zoom: int


class MapConfigResponse(BaseModel):
    provider: str
    street: MapLayerResponse | None
    satellite: MapLayerResponse | None
    hybrid: MapLayerResponse | None
    satellite_configured: bool