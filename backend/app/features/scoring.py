"""Feature engineering and scoring engine."""

import numpy as np
from app.models.schemas import PersonFeatures, PairwiseFeatures, WeightsConfig, AblationConfig
from app.cv.pipeline import CVPipelineOutput
from app.config import settings


class ScoringEngine:
    def __init__(self, weights: WeightsConfig | None = None):
        if weights is None:
            weights = WeightsConfig(
                dominance_w_expansion=settings.dominance_w_expansion,
                dominance_w_attention=settings.dominance_w_attention,
                dominance_w_emotion=settings.dominance_w_emotion,
                engagement_w_gaze=settings.engagement_w_gaze,
                engagement_w_closeness=settings.engagement_w_closeness,
                engagement_w_emotion_sim=settings.engagement_w_emotion_sim,
                balance_w_dominance_gap=settings.balance_w_dominance_gap,
                balance_w_gaze_asymmetry=settings.balance_w_gaze_asymmetry,
            )
        self.w = weights

    def compute(
        self, cv_output: CVPipelineOutput, ablation: AblationConfig | None = None
    ) -> PairwiseFeatures:
        if ablation is None:
            ablation = AblationConfig()

        p0, p1 = cv_output.persons[0], cv_output.persons[1]

        # 3D interpersonal distance
        distance_3d = self._compute_3d_distance(p0, p1, ablation)

        # Closeness score: inverse normalized
        closeness = self._closeness_score(distance_3d)

        # Expansion scores
        exp0 = self._expansion_score(p0, ablation)
        exp1 = self._expansion_score(p1, ablation)

        # Emotion similarity
        emotion_sim = self._emotion_similarity(p0, p1)

        # Gaze and attention
        a_to_b, b_to_a = cv_output.gaze_intersects
        mutual_gaze = cv_output.mutual_gaze

        incoming_0 = int(b_to_a)  # person 1 looks at person 0
        incoming_1 = int(a_to_b)  # person 0 looks at person 1

        # Dominance scores
        dom0 = self._dominance_score(exp0, incoming_0, p0.emotion_intensity)
        dom1 = self._dominance_score(exp1, incoming_1, p1.emotion_intensity)

        # Normalize dominance to 0-1
        dom_max = max(dom0, dom1, 1e-6)
        dom0_norm = dom0 / dom_max
        dom1_norm = dom1 / dom_max

        # Dominance gap
        dominance_gap = abs(dom0_norm - dom1_norm)

        # Engagement score
        engagement = self._engagement_score(
            mutual_gaze, closeness, emotion_sim, ablation
        )

        # Gaze asymmetry
        gaze_asym = abs(int(a_to_b) - int(b_to_a))

        # Balance index
        balance = self._balance_index(dominance_gap, gaze_asym)

        return PairwiseFeatures(
            distance_3d=distance_3d,
            closeness_score=closeness,
            expansion_scores=(exp0, exp1),
            emotion_similarity=emotion_sim,
            gaze_intersects=(a_to_b, b_to_a),
            mutual_gaze=mutual_gaze,
            incoming_attention=(incoming_0, incoming_1),
            dominance_scores=(dom0_norm, dom1_norm),
            dominance_gap=dominance_gap,
            engagement_score=engagement,
            balance_index=balance,
        )

    def _compute_3d_distance(
        self, p0: PersonFeatures, p1: PersonFeatures, ablation: AblationConfig
    ) -> float:
        """Euclidean distance in 3D (x, y, depth)."""
        pos0 = np.array(p0.position_3d)
        pos1 = np.array(p1.position_3d)

        if ablation.disable_depth:
            # Use only 2D distance
            return float(np.linalg.norm(pos0[:2] - pos1[:2]))

        # Weight depth difference more since it's less reliable
        diff = pos0 - pos1
        diff[2] *= 0.5  # reduce depth weight due to monocular estimation noise
        return float(np.linalg.norm(diff))

    @staticmethod
    def _closeness_score(distance_3d: float) -> float:
        """Inverse normalized distance. Closer = higher score."""
        # Using sigmoid-like normalization
        # Typical distances in normalized image coords: 0.1 (very close) to 0.8 (far)
        score = 1.0 / (1.0 + distance_3d * 5.0)
        return float(np.clip(score, 0.0, 1.0))

    @staticmethod
    def _expansion_score(person: PersonFeatures, ablation: AblationConfig) -> float:
        """Arm span / shoulder width ratio, normalized."""
        if ablation.disable_expansion:
            return 0.5  # neutral

        if person.shoulder_width < 1e-6:
            return 0.5

        ratio = person.arm_span / person.shoulder_width
        # Typical ratios: 1.0 (arms at sides) to 3.0+ (arms extended)
        normalized = float(np.clip((ratio - 1.0) / 2.0, 0.0, 1.0))
        return normalized

    @staticmethod
    def _emotion_similarity(p0: PersonFeatures, p1: PersonFeatures) -> float:
        """1 - |smile_a - smile_b|"""
        diff = abs(p0.smile_probability - p1.smile_probability)
        return float(1.0 - np.clip(diff, 0.0, 1.0))

    def _dominance_score(
        self, expansion: float, incoming_attention: int, emotion_intensity: float
    ) -> float:
        """Weighted dominance score for one person."""
        return (
            self.w.dominance_w_expansion * expansion
            + self.w.dominance_w_attention * incoming_attention
            + self.w.dominance_w_emotion * emotion_intensity
        )

    def _engagement_score(
        self,
        mutual_gaze: bool,
        closeness: float,
        emotion_sim: float,
        ablation: AblationConfig,
    ) -> float:
        """Weighted engagement score for the dyad."""
        gaze_val = 1.0 if mutual_gaze else 0.0
        if ablation.disable_gaze:
            gaze_val = 0.5  # neutral when disabled

        return (
            self.w.engagement_w_gaze * gaze_val
            + self.w.engagement_w_closeness * closeness
            + self.w.engagement_w_emotion_sim * emotion_sim
        )

    def _balance_index(self, dominance_gap: float, gaze_asymmetry: float) -> float:
        """1 - weighted(dominance_gap + gaze_asymmetry)."""
        imbalance = (
            self.w.balance_w_dominance_gap * dominance_gap
            + self.w.balance_w_gaze_asymmetry * gaze_asymmetry
        )
        return float(np.clip(1.0 - imbalance, 0.0, 1.0))
