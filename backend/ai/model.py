from __future__ import annotations

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from .feature_engineering import FEATURE_NAMES


class ExplainableMatchModel:
    """Replaceable supervised model trained only from generated feature examples."""

    def __init__(self) -> None:
        self.model = RandomForestClassifier(n_estimators=80, random_state=42, class_weight="balanced")
        self._fit_synthetic_feature_examples()

    def _fit_synthetic_feature_examples(self) -> None:
        rng = np.random.default_rng(42)
        match = np.clip(rng.normal(.9, .07, (300, len(FEATURE_NAMES))), 0, 1)
        possible = np.clip(rng.normal(.62, .12, (300, len(FEATURE_NAMES))), 0, 1)
        non_match = np.clip(rng.normal(.20, .12, (300, len(FEATURE_NAMES))), 0, 1)
        self.model.fit(np.vstack([match, possible, non_match]), np.array(["MATCH"] * 300 + ["POSSIBLE_MATCH"] * 300 + ["NON_MATCH"] * 300))

    def predict(self, features: dict[str, float]) -> dict[str, object]:
        values = np.array([[features[name] for name in FEATURE_NAMES]])
        probabilities = self.model.predict_proba(values)[0]
        classes = self.model.classes_.tolist()
        best = int(np.argmax(probabilities))
        return {"model_class": classes[best], "model_probability": round(float(probabilities[best]), 4), "model_label": "AI MODEL TRAINED ON SYNTHETIC DEMO DATA"}
