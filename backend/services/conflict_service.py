def potential_inconsistency(conflict_type: str, source_a: str | None, source_b: str | None) -> dict:
    return {"conflict_type": conflict_type, "source_a": source_a, "source_b": source_b, "description": "Potential inconsistency detected.", "status": "OPEN"}
