"""Evaluation metrics comparing model outputs to human annotations."""

import json
import numpy as np
from scipy import stats
from sqlalchemy.orm import Session

from app.models.database import Annotation, AnalysisCache
from app.models.schemas import EvaluationMetrics


class MetricsCalculator:
    def compute(self, db: Session) -> EvaluationMetrics:
        """Compute evaluation metrics from all annotations paired with cached analyses."""
        annotations = db.query(Annotation).all()
        caches = {c.image_id: c for c in db.query(AnalysisCache).all()}

        if not annotations:
            return EvaluationMetrics(num_annotations=0)

        # Collect paired data
        human_dominant = []
        model_dominant = []
        human_engagement = []
        model_engagement = []
        human_mutual = []
        model_mutual = []

        for ann in annotations:
            cache = caches.get(ann.image_id)
            if cache is None:
                continue

            # Dominance: human says person 0 or 1 is more dominant
            # Model: compare dominance_score_0 vs dominance_score_1
            human_dominant.append(ann.dominant_person)
            model_dom_diff = (cache.dominance_score_0 or 0) - (cache.dominance_score_1 or 0)
            # Convert to 0/1: if diff > 0, model says person 0 is dominant
            model_dominant.append(0 if model_dom_diff >= 0 else 1)

            # Engagement: human rates 1-5, model gives 0-1
            human_engagement.append(ann.interaction_strength)
            model_engagement.append((cache.engagement_score or 0.5) * 5.0)

            # Mutual gaze: boolean
            human_mutual.append(int(ann.mutual_attention))
            model_mutual.append(int(cache.mutual_gaze or False))

        n = len(human_dominant)
        if n == 0:
            return EvaluationMetrics(num_annotations=len(annotations))

        # Spearman rank correlation for dominance
        # Use the raw dominance score difference for ranking
        dom_rho, dom_p = None, None
        if n >= 3:
            try:
                result = stats.spearmanr(human_dominant, model_dominant)
                dom_rho = float(result.correlation) if not np.isnan(result.correlation) else None
                dom_p = float(result.pvalue) if not np.isnan(result.pvalue) else None
            except Exception:
                pass

        # MAE for engagement
        engagement_mae = None
        if human_engagement:
            engagement_mae = float(np.mean(np.abs(
                np.array(human_engagement) - np.array(model_engagement)
            )))

        # Binary accuracy for mutual gaze
        mutual_acc = None
        if human_mutual:
            correct = sum(1 for h, m in zip(human_mutual, model_mutual) if h == m)
            mutual_acc = float(correct / len(human_mutual))

        return EvaluationMetrics(
            dominance_spearman_rho=dom_rho,
            dominance_spearman_p=dom_p,
            engagement_mae=engagement_mae,
            mutual_gaze_accuracy=mutual_acc,
            num_annotations=n,
        )

    def compute_ablation(
        self, db: Session, ablation_results: dict[str, list[dict]]
    ) -> dict[str, EvaluationMetrics]:
        """Compute metrics for each ablation condition.

        ablation_results: {condition_name: [{image_id, dominance_0, dominance_1, engagement, mutual_gaze}]}
        """
        annotations = db.query(Annotation).all()
        ann_by_image = {}
        for a in annotations:
            ann_by_image.setdefault(a.image_id, []).append(a)

        results = {}
        for condition, analyses in ablation_results.items():
            human_dom, model_dom = [], []
            human_eng, model_eng = [], []
            human_mut, model_mut = [], []

            for analysis in analyses:
                img_id = analysis["image_id"]
                anns = ann_by_image.get(img_id, [])
                for ann in anns:
                    d0 = analysis.get("dominance_0", 0.5)
                    d1 = analysis.get("dominance_1", 0.5)
                    human_dom.append(ann.dominant_person)
                    model_dom.append(0 if d0 >= d1 else 1)

                    human_eng.append(ann.interaction_strength)
                    model_eng.append(analysis.get("engagement", 0.5) * 5.0)

                    human_mut.append(int(ann.mutual_attention))
                    model_mut.append(int(analysis.get("mutual_gaze", False)))

            n = len(human_dom)
            dom_rho, dom_p, eng_mae, mut_acc = None, None, None, None

            if n >= 3:
                try:
                    r = stats.spearmanr(human_dom, model_dom)
                    dom_rho = float(r.correlation) if not np.isnan(r.correlation) else None
                    dom_p = float(r.pvalue) if not np.isnan(r.pvalue) else None
                except Exception:
                    pass

            if human_eng:
                eng_mae = float(np.mean(np.abs(
                    np.array(human_eng) - np.array(model_eng)
                )))

            if human_mut:
                correct = sum(1 for h, m in zip(human_mut, model_mut) if h == m)
                mut_acc = float(correct / len(human_mut))

            results[condition] = EvaluationMetrics(
                dominance_spearman_rho=dom_rho,
                dominance_spearman_p=dom_p,
                engagement_mae=eng_mae,
                mutual_gaze_accuracy=mut_acc,
                num_annotations=n,
            )

        return results
