import os


def provider_status() -> dict[str, str | bool | None]:
    return {"configured": bool(os.getenv("SATELLITE_TILE_URL")), "provider": os.getenv("SATELLITE_PROVIDER"), "tile_url": os.getenv("SATELLITE_TILE_URL")}
