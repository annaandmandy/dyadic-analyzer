const API_BASE = "/api";

export interface PersonFeatures {
  person_id: number;
  center_2d: [number, number];
  depth: number;
  arm_span: number;
  shoulder_width: number;
  torso_alignment: number;
  smile_probability: number;
  emotion_intensity: number;
  face_yaw_angle: number;
  face_bbox: [number, number, number, number];
  gaze_direction: [number, number, number];
  position_3d: [number, number, number];
}

export interface PairwiseFeatures {
  distance_3d: number;
  closeness_score: number;
  expansion_scores: [number, number];
  emotion_similarity: number;
  gaze_intersects: [boolean, boolean];
  mutual_gaze: boolean;
  incoming_attention: [number, number];
  dominance_scores: [number, number];
  dominance_gap: number;
  engagement_score: number;
  balance_index: number;
  contact_score: number;
}

export interface VoiceThought {
  person_id: number;
  thought_text: string;
  tone: string;
  audio_url: string | null;
}

export interface AnalysisResult {
  image_id: string;
  persons: PersonFeatures[];
  pairwise: PairwiseFeatures;
  interpretation: {
    scene_context: string;
    explanation: string;
    one_line_summary: string;
  };
  voice_thoughts: VoiceThought[];
  disclaimer: string;
}

export interface AnnotationRequest {
  image_id: string;
  dominant_person: number;
  interaction_strength: number;
  mutual_attention: boolean;
}

export interface EvaluationMetrics {
  dominance_spearman_rho: number | null;
  dominance_spearman_p: number | null;
  engagement_mae: number | null;
  mutual_gaze_accuracy: number | null;
  num_annotations: number;
}

export async function analyzeImage(
  file: File,
  options: {
    useLlm?: boolean;
    generateAudio?: boolean;
    disableDepth?: boolean;
    disableGaze?: boolean;
    disableExpansion?: boolean;
  } = {}
): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);

  const params = new URLSearchParams();
  if (options.useLlm !== undefined) params.set("use_llm", String(options.useLlm));
  if (options.generateAudio !== undefined) params.set("generate_audio", String(options.generateAudio));
  if (options.disableDepth) params.set("disable_depth", "true");
  if (options.disableGaze) params.set("disable_gaze", "true");
  if (options.disableExpansion) params.set("disable_expansion", "true");

  const res = await fetch(`${API_BASE}/analyze?${params}`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Analysis failed");
  }

  return res.json();
}

export async function submitAnnotation(annotation: AnnotationRequest) {
  const res = await fetch(`${API_BASE}/annotations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(annotation),
  });
  if (!res.ok) throw new Error("Failed to submit annotation");
  return res.json();
}

export async function getEvaluationMetrics(): Promise<EvaluationMetrics> {
  const res = await fetch(`${API_BASE}/evaluate`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

export async function tuneWeights(method: "grid-search" | "regression") {
  const res = await fetch(`${API_BASE}/tune/${method}`, { method: "POST" });
  if (!res.ok) throw new Error("Tuning failed");
  return res.json();
}
