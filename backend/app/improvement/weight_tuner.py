"""Model improvement via weight tuning and linear regression."""

import json
import itertools
import numpy as np
from scipy import stats
from sklearn.linear_model import LinearRegression
from sqlalchemy.orm import Session

from app.models.database import Annotation, AnalysisCache, TunedWeights
from app.models.schemas import WeightsConfig


class WeightTuner:
    # Grid search ranges for each weight group
    DOMINANCE_GRID = [
        (0.5, 0.3, 0.2),
        (0.4, 0.3, 0.3),
        (0.3, 0.4, 0.3),
        (0.3, 0.3, 0.4),
        (0.4, 0.4, 0.2),
        (0.2, 0.4, 0.4),
        (0.6, 0.2, 0.2),
    ]

    ENGAGEMENT_GRID = [
        (0.5, 0.3, 0.2),
        (0.4, 0.3, 0.3),
        (0.3, 0.4, 0.3),
        (0.3, 0.3, 0.4),
        (0.4, 0.4, 0.2),
        (0.2, 0.4, 0.4),
        (0.6, 0.2, 0.2),
    ]

    def grid_search(self, db: Session) -> dict:
        """Find best weight configuration via grid search over annotations."""
        annotations = db.query(Annotation).all()
        caches = {c.image_id: c for c in db.query(AnalysisCache).all()}

        paired = []
        for ann in annotations:
            cache = caches.get(ann.image_id)
            if cache is None:
                continue
            result = json.loads(cache.result_json)
            paired.append((ann, result))

        if len(paired) < 3:
            return {"error": "Need at least 3 annotated images for tuning", "n": len(paired)}

        best_score = -1.0
        best_weights = None
        best_metrics = {}

        for dom_w in self.DOMINANCE_GRID:
            for eng_w in self.ENGAGEMENT_GRID:
                weights = WeightsConfig(
                    dominance_w_expansion=dom_w[0],
                    dominance_w_attention=dom_w[1],
                    dominance_w_emotion=dom_w[2],
                    engagement_w_gaze=eng_w[0],
                    engagement_w_closeness=eng_w[1],
                    engagement_w_emotion_sim=eng_w[2],
                )

                score, metrics = self._evaluate_weights(paired, weights)
                if score > best_score:
                    best_score = score
                    best_weights = weights
                    best_metrics = metrics

        if best_weights:
            self._save_weights(db, "grid_search_best", best_weights, best_metrics)

        return {
            "best_weights": best_weights.model_dump() if best_weights else None,
            "best_score": best_score,
            "metrics": best_metrics,
            "num_samples": len(paired),
        }

    def linear_regression_fit(self, db: Session) -> dict:
        """Fit linear regression to predict human dominance labels from features."""
        annotations = db.query(Annotation).all()
        caches = {c.image_id: c for c in db.query(AnalysisCache).all()}

        X = []
        y = []

        for ann in annotations:
            cache = caches.get(ann.image_id)
            if cache is None:
                continue

            result = json.loads(cache.result_json)
            pairwise = result.get("pairwise", {})

            # Features: expansion diff, attention diff, emotion diff
            exp = pairwise.get("expansion_scores", [0.5, 0.5])
            dom = pairwise.get("dominance_scores", [0.5, 0.5])
            gaze = pairwise.get("gaze_intersects", [False, False])
            persons = result.get("persons", [{}, {}])

            features = [
                exp[0] - exp[1],
                int(gaze[1]) - int(gaze[0]),  # who receives more attention
                persons[0].get("emotion_intensity", 0.5) - persons[1].get("emotion_intensity", 0.5),
            ]

            X.append(features)
            # Target: 1 if person 0 is dominant, 0 if person 1
            y.append(1.0 if ann.dominant_person == 0 else 0.0)

        if len(X) < 3:
            return {"error": "Need at least 3 samples", "n": len(X)}

        X = np.array(X)
        y = np.array(y)

        reg = LinearRegression()
        reg.fit(X, y)

        # Map regression coefficients back to weight interpretation
        coefs = reg.coef_
        intercept = reg.intercept_

        # Normalize coefficients to get weight proportions
        abs_coefs = np.abs(coefs)
        total = abs_coefs.sum()
        if total > 1e-6:
            normalized = abs_coefs / total
        else:
            normalized = np.array([1 / 3, 1 / 3, 1 / 3])

        derived_weights = WeightsConfig(
            dominance_w_expansion=float(normalized[0]),
            dominance_w_attention=float(normalized[1]),
            dominance_w_emotion=float(normalized[2]),
        )

        r_squared = float(reg.score(X, y))

        self._save_weights(
            db, "linear_regression",
            derived_weights,
            {"r_squared": r_squared, "coefficients": coefs.tolist(), "intercept": float(intercept)},
        )

        return {
            "weights": derived_weights.model_dump(),
            "r_squared": r_squared,
            "coefficients": coefs.tolist(),
            "intercept": float(intercept),
            "num_samples": len(X),
        }

    def _evaluate_weights(
        self, paired: list[tuple], weights: WeightsConfig
    ) -> tuple[float, dict]:
        """Evaluate a weight config against human annotations. Returns (score, metrics)."""
        from app.features.scoring import ScoringEngine

        human_dom = []
        model_dom_diff = []

        for ann, result in paired:
            pairwise = result.get("pairwise", {})
            exp = pairwise.get("expansion_scores", [0.5, 0.5])
            gaze = pairwise.get("gaze_intersects", [False, False])
            persons = result.get("persons", [{}, {}])

            # Recompute dominance with new weights
            dom0 = (
                weights.dominance_w_expansion * exp[0]
                + weights.dominance_w_attention * int(gaze[1])
                + weights.dominance_w_emotion * persons[0].get("emotion_intensity", 0.5)
            )
            dom1 = (
                weights.dominance_w_expansion * exp[1]
                + weights.dominance_w_attention * int(gaze[0])
                + weights.dominance_w_emotion * persons[1].get("emotion_intensity", 0.5)
            )

            human_dom.append(ann.dominant_person)
            model_dom_diff.append(dom0 - dom1)

        # Spearman correlation between human labels and model score difference
        if len(human_dom) < 3:
            return 0.0, {}

        # Convert human labels to direction: 0 → positive, 1 → negative
        human_direction = [1.0 if h == 0 else -1.0 for h in human_dom]

        try:
            rho, p = stats.spearmanr(human_direction, model_dom_diff)
            if np.isnan(rho):
                return 0.0, {}
            return abs(rho), {"spearman_rho": float(rho), "p_value": float(p)}
        except Exception:
            return 0.0, {}

    @staticmethod
    def _save_weights(db: Session, name: str, weights: WeightsConfig, metrics: dict):
        """Save tuned weights to database."""
        existing = db.query(TunedWeights).filter_by(name=name).first()
        if existing:
            existing.weights_json = json.dumps(weights.model_dump())
            existing.metrics_json = json.dumps(metrics)
        else:
            entry = TunedWeights(
                name=name,
                weights_json=json.dumps(weights.model_dump()),
                metrics_json=json.dumps(metrics),
            )
            db.add(entry)
        db.commit()

    @staticmethod
    def load_weights(db: Session, name: str) -> WeightsConfig | None:
        """Load saved tuned weights."""
        entry = db.query(TunedWeights).filter_by(name=name).first()
        if entry is None:
            return None
        data = json.loads(entry.weights_json)
        return WeightsConfig(**data)
