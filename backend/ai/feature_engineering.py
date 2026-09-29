from __future__ import annotations

from rapidfuzz.fuzz import ratio

FEATURE_NAMES = ["owner_similarity", "address_similarity", "parcel_similarity", "survey_similarity", "khasra_similarity", "area_similarity", "land_use_similarity", "gis_similarity"]
WEIGHTS = {"owner_similarity": .20, "address_similarity": .10, "parcel_similarity": .18, "survey_similarity": .10, "khasra_similarity": .07, "area_similarity": .15, "land_use_similarity": .05, "gis_similarity": .15}


def similarity(left: object, right: object) -> float:
    return ratio(str(left or "").lower().strip(), str(right or "").lower().strip()) / 100


def area_similarity(left: float | None, right: float | None) -> float:
    if not left or not right:
        return 0.0
    return max(0.0, 1.0 - abs(left - right) / max(left, right))


def build_features(left: dict, right: dict) -> dict[str, float]:
    return {
        "owner_similarity": similarity(left.get("owner_name"), right.get("owner_name")),
        "address_similarity": similarity(left.get("address"), right.get("address")),
        "parcel_similarity": similarity(left.get("parcel_id"), right.get("parcel_id")),
        "survey_similarity": similarity(left.get("survey_number"), right.get("survey_number")),
        "khasra_similarity": similarity(left.get("khasra_number"), right.get("khasra_number")),
        "area_similarity": area_similarity(left.get("area_sq_m"), right.get("area_sq_m")),
        "land_use_similarity": similarity(left.get("land_use"), right.get("land_use")),
        "gis_similarity": similarity(left.get("geometry"), right.get("geometry")),
    }
