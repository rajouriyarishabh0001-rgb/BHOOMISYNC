from __future__ import annotations


def unavailable_analysis(parcel_id: str, provider: str | None) -> dict:
    return {"parcel_id": parcel_id, "analysis_status": "UNAVAILABLE", "provider": provider, "land_cover_estimate": None, "built_up_indicator": None, "vegetation_indicator": None, "water_indicator": None, "possible_change": None, "confidence": None, "explanation": "No configured satellite provider is available. Configure SATELLITE_TILE_URL and an authorized analysis service before interpreting imagery."}
