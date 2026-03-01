"""FastAPI route definitions."""

import json
import os
import uuid

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db, Annotation, AnalysisCache
from app.models.schemas import (
    AnalysisResult,
    AnnotationRequest,
    AnnotationResponse,
    WeightsConfig,
    AblationConfig,
    EvaluationMetrics,
    GroupDetectionResult,
)
from app.cv.pipeline import CVPipeline
from app.features.scoring import ScoringEngine
from app.llm.interpreter import LLMInterpreter
from app.tts.voice_sim import VoiceSimulator
from app.evaluation.metrics import MetricsCalculator
from app.improvement.weight_tuner import WeightTuner

router = APIRouter()

# Lazy-initialized singletons
_cv_pipeline: CVPipeline | None = None
_llm_interpreter: LLMInterpreter | None = None
_voice_simulator: VoiceSimulator | None = None


def get_cv_pipeline() -> CVPipeline:
    global _cv_pipeline
    if _cv_pipeline is None:
        _cv_pipeline = CVPipeline()
    return _cv_pipeline


def get_llm_interpreter() -> LLMInterpreter:
    global _llm_interpreter
    if _llm_interpreter is None:
        _llm_interpreter = LLMInterpreter()
    return _llm_interpreter


def get_voice_simulator() -> VoiceSimulator:
    global _voice_simulator
    if _voice_simulator is None:
        _voice_simulator = VoiceSimulator()
    return _voice_simulator


@router.post("/detect", response_model=GroupDetectionResult)
async def detect_persons(file: UploadFile = File(...)):
    """Detect all persons in an image using YOLO. Returns bounding boxes for person selection."""
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are supported.")

    contents = await file.read()
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {settings.max_upload_size_mb}MB.")

    nparr = np.frombuffer(contents, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(400, "Could not decode image.")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # Save upload so the frontend can display it
    os.makedirs(settings.upload_dir, exist_ok=True)
    image_id = uuid.uuid4().hex[:12]
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
    save_path = os.path.join(settings.upload_dir, f"{image_id}.{ext}")
    with open(save_path, "wb") as f:
        f.write(contents)

    pipeline = get_cv_pipeline()
    persons = pipeline.detect_only(image_rgb)

    if len(persons) < 2:
        raise HTTPException(
            422,
            f"Need at least 2 people in the image. Detected {len(persons)}.",
        )

    return GroupDetectionResult(image_id=image_id, persons=persons)


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_image(
    file: UploadFile = File(...),
    use_llm: bool = Query(True, description="Use LLM for interpretation"),
    generate_audio: bool = Query(True, description="Generate TTS audio"),
    disable_depth: bool = Query(False),
    disable_gaze: bool = Query(False),
    disable_expansion: bool = Query(False),
    person_0: int = Query(0, description="Index of first person to analyze (left-to-right)"),
    person_1: int = Query(1, description="Index of second person to analyze (left-to-right)"),
    db: Session = Depends(get_db),
):
    """Analyze a dyadic image and return interaction signals."""
    # Validate file
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Only JPEG, PNG, and WebP images are supported.")

    contents = await file.read()
    if len(contents) > settings.max_upload_size_mb * 1024 * 1024:
        raise HTTPException(400, f"File too large. Max {settings.max_upload_size_mb}MB.")

    # Decode image
    nparr = np.frombuffer(contents, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(400, "Could not decode image.")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    # Save upload
    os.makedirs(settings.upload_dir, exist_ok=True)
    image_id = uuid.uuid4().hex[:12]
    ext = file.filename.rsplit(".", 1)[-1] if file.filename else "jpg"
    save_path = os.path.join(settings.upload_dir, f"{image_id}.{ext}")
    with open(save_path, "wb") as f:
        f.write(contents)

    # Run CV pipeline
    ablation = AblationConfig(
        disable_depth=disable_depth,
        disable_gaze=disable_gaze,
        disable_expansion=disable_expansion,
    )

    try:
        pipeline = get_cv_pipeline()
        cv_output = pipeline.process(image_rgb, ablation, person_indices=(person_0, person_1))
    except ValueError as e:
        raise HTTPException(422, str(e))

    # Feature scoring
    scoring = ScoringEngine()
    pairwise = scoring.compute(cv_output, ablation)

    # LLM interpretation (vision-based when image available)
    interpreter = get_llm_interpreter()
    if use_llm and settings.openai_api_key:
        interpretation = await interpreter.interpret(cv_output.persons, pairwise, contents, ext)
    else:
        interpretation = interpreter.interpret_sync_fallback(cv_output.persons, pairwise)

    # Generate contextual voice thoughts via LLM vision (text only)
    pregenerated_thoughts = None
    if use_llm and settings.openai_api_key:
        pregenerated_thoughts = await interpreter.generate_voice_thoughts(
            contents, ext, cv_output.persons, pairwise, interpretation.explanation
        )

    # Voice simulation (TTS audio synthesis)
    voice_sim = get_voice_simulator()
    voice_thoughts = await voice_sim.process_both(
        cv_output.persons, pairwise, pregenerated_thoughts, generate_audio=generate_audio
    )

    result = AnalysisResult(
        image_id=image_id,
        persons=cv_output.persons,
        pairwise=pairwise,
        interpretation=interpretation,
        voice_thoughts=voice_thoughts,
    )

    # Cache result
    cache_entry = AnalysisCache(
        image_id=image_id,
        result_json=result.model_dump_json(),
        dominance_score_0=pairwise.dominance_scores[0],
        dominance_score_1=pairwise.dominance_scores[1],
        engagement_score=pairwise.engagement_score,
        mutual_gaze=pairwise.mutual_gaze,
    )
    db.add(cache_entry)
    db.commit()

    return result


@router.get("/analysis/{image_id}", response_model=AnalysisResult)
async def get_analysis(image_id: str, db: Session = Depends(get_db)):
    """Retrieve a cached analysis result."""
    cache = db.query(AnalysisCache).filter_by(image_id=image_id).first()
    if not cache:
        raise HTTPException(404, "Analysis not found.")
    return AnalysisResult.model_validate_json(cache.result_json)


@router.post("/annotations", response_model=AnnotationResponse)
async def create_annotation(req: AnnotationRequest, db: Session = Depends(get_db)):
    """Submit a human annotation for an analyzed image."""
    ann = Annotation(
        image_id=req.image_id,
        dominant_person=req.dominant_person,
        interaction_strength=req.interaction_strength,
        mutual_attention=req.mutual_attention,
    )
    db.add(ann)
    db.commit()
    db.refresh(ann)

    return AnnotationResponse(
        id=ann.id,
        image_id=ann.image_id,
        dominant_person=ann.dominant_person,
        interaction_strength=ann.interaction_strength,
        mutual_attention=ann.mutual_attention,
    )


@router.get("/annotations", response_model=list[AnnotationResponse])
async def list_annotations(
    image_id: str | None = None,
    db: Session = Depends(get_db),
):
    """List annotations, optionally filtered by image_id."""
    query = db.query(Annotation)
    if image_id:
        query = query.filter_by(image_id=image_id)
    return [
        AnnotationResponse(
            id=a.id,
            image_id=a.image_id,
            dominant_person=a.dominant_person,
            interaction_strength=a.interaction_strength,
            mutual_attention=a.mutual_attention,
        )
        for a in query.all()
    ]


@router.get("/evaluate", response_model=EvaluationMetrics)
async def evaluate(db: Session = Depends(get_db)):
    """Compute evaluation metrics from all annotations."""
    calc = MetricsCalculator()
    return calc.compute(db)


@router.post("/tune/grid-search")
async def tune_grid_search(db: Session = Depends(get_db)):
    """Run grid search weight tuning."""
    tuner = WeightTuner()
    return tuner.grid_search(db)


@router.post("/tune/regression")
async def tune_regression(db: Session = Depends(get_db)):
    """Run linear regression weight fitting."""
    tuner = WeightTuner()
    return tuner.linear_regression_fit(db)


@router.get("/weights/{name}")
async def get_weights(name: str, db: Session = Depends(get_db)):
    """Load saved tuned weights."""
    tuner = WeightTuner()
    weights = tuner.load_weights(db, name)
    if weights is None:
        raise HTTPException(404, f"Weights '{name}' not found.")
    return weights.model_dump()


@router.get("/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files."""
    path = os.path.join(settings.audio_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Audio file not found.")
    return FileResponse(path, media_type="audio/mpeg")


@router.get("/uploads/{filename}")
async def serve_upload(filename: str):
    """Serve uploaded images."""
    path = os.path.join(settings.upload_dir, filename)
    if not os.path.isfile(path):
        raise HTTPException(404, "Image not found.")
    return FileResponse(path)


@router.get("/health")
async def health():
    return {"status": "ok"}
