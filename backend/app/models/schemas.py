"""Pydantic schemas for request/response models."""

from pydantic import BaseModel, Field
from typing import Optional


class PersonFeatures(BaseModel):
    person_id: int
    center_2d: tuple[float, float]
    depth: float
    arm_span: float
    shoulder_width: float
    torso_alignment: float
    smile_probability: float
    emotion_intensity: float
    face_yaw_angle: float
    face_bbox: tuple[float, float, float, float]
    gaze_direction: tuple[float, float, float]
    position_3d: tuple[float, float, float]


class PairwiseFeatures(BaseModel):
    distance_3d: float
    closeness_score: float
    expansion_scores: tuple[float, float]
    emotion_similarity: float
    gaze_intersects: tuple[bool, bool]
    mutual_gaze: bool
    incoming_attention: tuple[int, int]
    dominance_scores: tuple[float, float]
    dominance_gap: float
    engagement_score: float
    balance_index: float


class InteractionSummary(BaseModel):
    explanation: str
    one_line_summary: str


class VoiceThought(BaseModel):
    person_id: int
    thought_text: str
    tone: str
    audio_url: Optional[str] = None


class AnalysisResult(BaseModel):
    image_id: str
    persons: list[PersonFeatures]
    pairwise: PairwiseFeatures
    interpretation: InteractionSummary
    voice_thoughts: list[VoiceThought]
    disclaimer: str = (
        "This system models perceived visual interaction signals and does not "
        "determine real relationships or psychological states."
    )


class AnnotationRequest(BaseModel):
    image_id: str
    dominant_person: int = Field(ge=0, le=1)
    interaction_strength: int = Field(ge=1, le=5)
    mutual_attention: bool


class AnnotationResponse(BaseModel):
    id: int
    image_id: str
    dominant_person: int
    interaction_strength: int
    mutual_attention: bool


class WeightsConfig(BaseModel):
    dominance_w_expansion: float = 0.4
    dominance_w_attention: float = 0.3
    dominance_w_emotion: float = 0.3
    engagement_w_gaze: float = 0.4
    engagement_w_closeness: float = 0.3
    engagement_w_emotion_sim: float = 0.3
    balance_w_dominance_gap: float = 0.5
    balance_w_gaze_asymmetry: float = 0.5


class AblationConfig(BaseModel):
    disable_depth: bool = False
    disable_gaze: bool = False
    disable_expansion: bool = False


class EvaluationMetrics(BaseModel):
    dominance_spearman_rho: Optional[float] = None
    dominance_spearman_p: Optional[float] = None
    engagement_mae: Optional[float] = None
    mutual_gaze_accuracy: Optional[float] = None
    num_annotations: int = 0
