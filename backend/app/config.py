"""Application configuration with environment variable overrides."""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # OpenAI / LLM
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"

    # ElevenLabs TTS
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_confident: str = "pNInz6obpgDQGcFmaJgB"  # Adam
    elevenlabs_voice_warm: str = "EXAVITQu4vr4xnSDxMaL"      # Bella
    elevenlabs_voice_reserved: str = "VR6AewLTigWG4xSOukaG"   # Arnold

    # CV Pipeline
    face_detection_backend: str = "mediapipe"  # "retinaface" or "mediapipe"
    midas_model_type: str = "MiDaS_small"
    pose_model_complexity: int = 1
    yolo_model: str = "yolov8m.pt"
    yolo_conf: float = 0.15
    yolo_imgsz: int = 1280

    # Scoring weights (configurable)
    dominance_w_expansion: float = 0.4
    dominance_w_attention: float = 0.3
    dominance_w_emotion: float = 0.3
    engagement_w_gaze: float = 0.4
    engagement_w_closeness: float = 0.3
    engagement_w_emotion_sim: float = 0.3
    balance_w_dominance_gap: float = 0.5
    balance_w_gaze_asymmetry: float = 0.5

    # Database
    database_url: str = "sqlite:///./dyadic_analyzer.db"

    # File storage
    upload_dir: str = "./uploads"
    audio_dir: str = "./audio_output"
    max_upload_size_mb: int = 10

    model_config = {"env_file": ".env", "env_prefix": "DYADIC_"}


settings = Settings()
