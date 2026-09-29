import os


def public_map_config() -> dict[str, str | None]:
    return {"provider": os.getenv("MAP_PROVIDER", "osm"), "tile_url": os.getenv("MAP_TILE_URL"), "satellite_tile_url": os.getenv("SATELLITE_TILE_URL"), "attribution": "Configured provider attribution"}
