from rapidfuzz.fuzz import ratio


def fuzzy_score(query: str, value: str | None) -> float:
    return ratio(query.lower().strip(), (value or "").lower().strip()) / 100
