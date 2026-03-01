# Dyadic Visual Social Signal Analyzer

Analyzes **perceived visual interaction signals** between two people from a single image. Uses computer vision (face detection, pose estimation, depth estimation, gaze analysis), feature engineering, LLM interpretation, and voice simulation.

> **Disclaimer:** This system models perceived visual interaction signals and does not determine real relationships or psychological states.

## Architecture

```
Frontend (React + Vite)         Backend (Python FastAPI)
 - Image upload                  - CV Pipeline (MediaPipe, MiDaS)
 - Score dashboard               - Feature Engineering / Scoring
 - 3D visualization (Three.js)   - LLM Interpretation (OpenAI)
 - Audio playback                 - Voice Simulation (ElevenLabs)
 - Annotation form                - Evaluation & Weight Tuning
```

## Project Structure

```
dyadic-analyzer/
├── backend/
│   ├── app/
│   │   ├── api/routes.py          # FastAPI endpoints
│   │   ├── cv/
│   │   │   ├── face_detection.py  # MediaPipe / RetinaFace
│   │   │   ├── pose_estimation.py # MediaPipe Pose
│   │   │   ├── depth_estimation.py# MiDaS monocular depth
│   │   │   ├── gaze_estimation.py # Gaze direction & intersection
│   │   │   └── pipeline.py        # Orchestrator
│   │   ├── features/scoring.py    # Feature engineering & scoring
│   │   ├── llm/interpreter.py     # LLM interpretation layer
│   │   ├── tts/voice_sim.py       # ElevenLabs TTS integration
│   │   ├── evaluation/metrics.py  # Spearman, MAE, accuracy
│   │   ├── improvement/weight_tuner.py # Grid search & regression
│   │   ├── models/
│   │   │   ├── schemas.py         # Pydantic models
│   │   │   └── database.py        # SQLAlchemy models
│   │   ├── config.py              # Settings with env overrides
│   │   └── main.py                # App entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ImageUpload.tsx
│   │   │   ├── ResultDashboard.tsx
│   │   │   ├── InteractionVisualization.tsx
│   │   │   ├── AudioPlayer.tsx
│   │   │   ├── AnnotationForm.tsx
│   │   │   └── Disclaimer.tsx
│   │   ├── utils/api.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── Dockerfile
│   └── vite.config.ts
├── docker-compose.yml
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- (Optional) OpenAI API key for LLM interpretation
- (Optional) ElevenLabs API key for voice simulation

### Backend Setup (with `uv` — recommended, 10x faster!)

```bash
cd backend

# Install uv (https://docs.astral.sh/uv/getting-started/)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create venv and install all dependencies
uv venv
source .venv/bin/activate    # macOS/Linux: .venv\Scripts\activate (Windows)
uv pip install -e .

cp .env.example .env
# Edit .env with your API keys

uvicorn app.main:app --reload --port 8000
```

**Or with traditional pip:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

See [QUICKSTART_UV.md](./QUICKSTART_UV.md) for more `uv` tips.

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### Docker

```bash
# From project root
docker-compose up --build
```

Frontend: http://localhost:3000 | Backend API: http://localhost:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analyze` | Analyze an uploaded image |
| GET | `/api/analysis/{id}` | Retrieve cached analysis |
| POST | `/api/annotations` | Submit human annotation |
| GET | `/api/annotations` | List annotations |
| GET | `/api/evaluate` | Compute evaluation metrics |
| POST | `/api/tune/grid-search` | Run grid search weight tuning |
| POST | `/api/tune/regression` | Fit linear regression weights |
| GET | `/api/weights/{name}` | Load saved tuned weights |
| GET | `/api/health` | Health check |

## CV Pipeline

For each person detected:
- 2D center coordinates (face bounding box)
- Depth via MiDaS (median depth in face region)
- Arm span and shoulder width via MediaPipe Pose
- Torso vertical alignment
- Smile probability (mouth geometry)
- Face yaw angle (landmark asymmetry)
- Gaze direction vector (3D)

Pairwise computation:
- 3D interpersonal distance
- Gaze intersection with other person's bounding box
- Mutual gaze detection

## Scoring Features

| Feature | Formula |
|---------|---------|
| Closeness | `1 / (1 + distance_3d * 5)` |
| Expansion | `(arm_span / shoulder_width - 1) / 2` |
| Emotion Similarity | `1 - abs(smile_a - smile_b)` |
| Dominance (per person) | `0.4*Expansion + 0.3*IncomingAttention + 0.3*EmotionIntensity` |
| Engagement | `0.4*MutualGaze + 0.3*Closeness + 0.3*EmotionSimilarity` |
| Balance Index | `1 - (0.5*DominanceGap + 0.5*GazeAsymmetry)` |

All weights are configurable via environment variables or the tuning API.

## Evaluation

### Human Annotation

The annotation form collects:
1. Who appears more dominant? (Person 0 / Person 1)
2. Rate interaction strength (1-5)
3. Are both mutually attentive? (Yes/No)

### Metrics

- **Dominance:** Spearman rank correlation between model score and human vote
- **Engagement:** Mean Absolute Error vs. human rating
- **Mutual Gaze:** Binary accuracy

### Ablation Mode

Disable individual pipeline components via query parameters:
- `disable_depth=true` — removes depth estimation
- `disable_gaze=true` — removes gaze analysis
- `disable_expansion=true` — removes arm span / expansion

Compare metrics across conditions to measure feature contribution.

## Model Improvement

### Grid Search

```bash
curl -X POST http://localhost:8000/api/tune/grid-search
```

Searches over predefined weight combinations and selects the configuration with the highest Spearman correlation to human dominance labels.

### Linear Regression

```bash
curl -X POST http://localhost:8000/api/tune/regression
```

Fits a linear regression from (expansion_diff, attention_diff, emotion_diff) to human dominance labels. Reports R-squared and derived weights.

### Adding New Features

1. Add extraction logic in `backend/app/cv/` or new submodule
2. Add the feature to `PersonFeatures` or `PairwiseFeatures` in `schemas.py`
3. Incorporate into `ScoringEngine.compute()` in `scoring.py`
4. Update the LLM prompt template in `interpreter.py`
5. Collect new annotations and retune weights

## Example Output JSON

```json
{
  "image_id": "a1b2c3d4e5f6",
  "persons": [
    {
      "person_id": 0,
      "center_2d": [0.32, 0.45],
      "depth": 0.62,
      "arm_span": 0.35,
      "shoulder_width": 0.18,
      "torso_alignment": 0.92,
      "smile_probability": 0.78,
      "emotion_intensity": 0.78,
      "face_yaw_angle": -12.3,
      "face_bbox": [0.22, 0.2, 0.42, 0.55],
      "gaze_direction": [0.21, -0.05, -0.98],
      "position_3d": [0.32, 0.45, 0.62]
    },
    {
      "person_id": 1,
      "center_2d": [0.68, 0.42],
      "depth": 0.58,
      "arm_span": 0.28,
      "shoulder_width": 0.16,
      "torso_alignment": 0.88,
      "smile_probability": 0.65,
      "emotion_intensity": 0.65,
      "face_yaw_angle": 15.7,
      "face_bbox": [0.58, 0.18, 0.78, 0.52],
      "gaze_direction": [-0.27, -0.03, -0.96],
      "position_3d": [0.68, 0.42, 0.58]
    }
  ],
  "pairwise": {
    "distance_3d": 0.36,
    "closeness_score": 0.36,
    "expansion_scores": [0.47, 0.38],
    "emotion_similarity": 0.87,
    "gaze_intersects": [true, true],
    "mutual_gaze": true,
    "incoming_attention": [1, 1],
    "dominance_scores": [0.72, 0.58],
    "dominance_gap": 0.14,
    "engagement_score": 0.67,
    "balance_index": 0.86
  },
  "interpretation": {
    "explanation": "Both individuals appear to be directing their gaze toward each other, suggesting mutual visual attention. They are positioned at moderate proximity with similar levels of facial expressiveness (emotion similarity at 0.87). Person 0 displays a slightly more expansive posture, reflected in a marginally higher perceived dominance score. Overall, the interaction pattern suggests an engaged and relatively balanced visual exchange.",
    "one_line_summary": "Mutually attentive visual exchange with balanced engagement and moderate proximity."
  },
  "voice_thoughts": [
    {
      "person_id": 0,
      "thought_text": "It's nice to share this moment of attention together.",
      "tone": "warm",
      "audio_url": "/audio/person_0_abc12345.mp3"
    },
    {
      "person_id": 1,
      "thought_text": "I sense a gentle ease in how we're standing together.",
      "tone": "warm",
      "audio_url": "/audio/person_1_def67890.mp3"
    }
  ],
  "disclaimer": "This system models perceived visual interaction signals and does not determine real relationships or psychological states."
}
```

## Ethical Safeguards

- No relationship classification (couple, friends, etc.)
- No psychological state inference
- No mental health diagnosis
- All outputs framed as "perceived visual interaction patterns"
- Disclaimer displayed prominently in UI and included in every API response
- Configurable, transparent scoring weights
- Human annotation pipeline for accountability
