from typing import Any

from fastapi import APIRouter, HTTPException

from ai.matcher import match_records

router = APIRouter(prefix="/api/ai", tags=["AI matching"])


@router.post("/match")
def match(payload: dict[str, Any]) -> dict[str, Any]:
    left = payload.get("left") or payload.get("source_a")
    right = payload.get("right") or payload.get("source_b")
    if not isinstance(left, dict) or not isinstance(right, dict):
        parcel_id = payload.get("parcel_id")
        if not parcel_id:
            raise HTTPException(422, "Provide source_a and source_b records or a parcel_id")
        left = {"parcel_id": parcel_id}
        right = {"parcel_id": parcel_id}
    result = match_records(left, right)
    result["disclaimer"] = "AI-assisted candidate match; manual verification is required and no legal ownership decision is made."
    return result
