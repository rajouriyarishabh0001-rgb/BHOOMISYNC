from __future__ import annotations

from .feature_engineering import WEIGHTS, build_features


def score_features(features: dict[str, float]) -> float:
    return round(sum(features[name] * weight for name, weight in WEIGHTS.items()), 4)


def explain(features: dict[str, float], score: float) -> list[str]:
    reasons = []
    if features["parcel_similarity"] >= .95: reasons.append("Same parcel identifier")
    if features["owner_similarity"] >= .85: reasons.append("Owner names highly similar")
    if features["area_similarity"] >= .9: reasons.append("Area difference is below the review threshold")
    if features["land_use_similarity"] >= .9: reasons.append("Same land-use classification")
    if features["gis_similarity"] >= .85: reasons.append("GIS geometry is highly similar")
    if not reasons: reasons.append("Candidate requires manual comparison across source fields")
    return reasons


def match_records(left: dict, right: dict) -> dict:
    features = build_features(left, right)
    score = score_features(features)
    level = "HIGH" if score >= .85 else "MEDIUM" if score >= .60 else "LOW"
    match_class = "MATCH" if score >= .85 else "POSSIBLE_MATCH" if score >= .60 else "NON_MATCH"
    return {"match_score": round(score * 100, 2), "match_probability": score, "confidence_level": level, "match_class": match_class, "matching_factors": features, "explanation": explain(features, score)}
