"""LLM interpretation layer for visual interaction metrics."""

import base64
import json
from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import PairwiseFeatures, PersonFeatures, InteractionSummary

SYSTEM_PROMPT = """You are an expert in nonverbal communication analysis. You interpret
quantified visual interaction metrics from images of two people.

STRICT RULES:
- Do NOT assume or classify relationship types (e.g., couple, friends, colleagues).
- Do NOT infer psychological states, mental health, or emotional well-being.
- Only describe observable behavioral patterns derived from the metrics.
- Frame all outputs as "perceived visual interaction patterns".
- Be precise, objective, and grounded in the provided data."""

VOICE_THOUGHT_PROMPT = """Look at this image of two people and read the interaction analysis below.

Interaction analysis:
{scene_explanation}

Key signals:
- Person 0 dominance: {dom0:.2f}, Person 1 dominance: {dom1:.2f}
- Engagement: {engagement:.2f}, Closeness: {closeness:.2f}, Mutual gaze: {mutual_gaze}
- Person 0 smile: {smile0:.2f}, Person 1 smile: {smile1:.2f}

Based on what you can actually SEE in the image (the setting, what they're doing, their body language, \
the context) and the signals above, write a brief first-person internal thought for each person — \
what they might be thinking or feeling in this specific moment. Make it feel real and specific to \
this scene, not generic. 1-2 sentences each.

Also assign a tone for each: "confident" (assertive, self-assured), "warm" (open, engaged, friendly), \
or "reserved" (withdrawn, cautious, distant).

Respond in JSON:
{{
  "person_0": {{"thought": "...", "tone": "confident|warm|reserved"}},
  "person_1": {{"thought": "...", "tone": "confident|warm|reserved"}}
}}"""

INTERPRETATION_TEMPLATE = """Interpret the following quantified visual interaction metrics
for two people detected in a single image. Do not assume relationship types. Focus only
on observable behavioral patterns. Avoid psychological diagnosis.

## Person 0 Features:
- Position (2D): {p0_center}
- Estimated depth: {p0_depth:.3f}
- Arm span / shoulder width (expansion): {p0_expansion:.3f}
- Smile probability: {p0_smile:.3f}
- Emotion intensity: {p0_emotion:.3f}
- Face yaw angle: {p0_yaw:.1f} degrees
- Gaze direction vector: {p0_gaze}

## Person 1 Features:
- Position (2D): {p1_center}
- Estimated depth: {p1_depth:.3f}
- Arm span / shoulder width (expansion): {p1_expansion:.3f}
- Smile probability: {p1_smile:.3f}
- Emotion intensity: {p1_emotion:.3f}
- Face yaw angle: {p1_yaw:.1f} degrees
- Gaze direction vector: {p1_gaze}

## Pairwise Metrics:
- 3D interpersonal distance: {distance_3d:.3f}
- Closeness score: {closeness:.3f}
- Emotion similarity: {emotion_sim:.3f}
- Person 0 gazes at Person 1: {gaze_0_to_1}
- Person 1 gazes at Person 0: {gaze_1_to_0}
- Mutual gaze: {mutual_gaze}
- Dominance scores: Person 0 = {dom0:.3f}, Person 1 = {dom1:.3f}
- Dominance gap: {dom_gap:.3f}
- Engagement score: {engagement:.3f}
- Balance index: {balance:.3f}

Respond in JSON with exactly two fields:
- "explanation": A 3-5 sentence analysis of the perceived visual interaction patterns.
- "one_line_summary": A single sentence summary of the perceived interaction."""


class LLMInterpreter:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def interpret(
        self,
        persons: list[PersonFeatures],
        pairwise: PairwiseFeatures,
    ) -> InteractionSummary:
        p0, p1 = persons[0], persons[1]

        prompt = INTERPRETATION_TEMPLATE.format(
            p0_center=f"({p0.center_2d[0]:.3f}, {p0.center_2d[1]:.3f})",
            p0_depth=p0.depth,
            p0_expansion=pairwise.expansion_scores[0],
            p0_smile=p0.smile_probability,
            p0_emotion=p0.emotion_intensity,
            p0_yaw=p0.face_yaw_angle,
            p0_gaze=f"({p0.gaze_direction[0]:.3f}, {p0.gaze_direction[1]:.3f}, {p0.gaze_direction[2]:.3f})",
            p1_center=f"({p1.center_2d[0]:.3f}, {p1.center_2d[1]:.3f})",
            p1_depth=p1.depth,
            p1_expansion=pairwise.expansion_scores[1],
            p1_smile=p1.smile_probability,
            p1_emotion=p1.emotion_intensity,
            p1_yaw=p1.face_yaw_angle,
            p1_gaze=f"({p1.gaze_direction[0]:.3f}, {p1.gaze_direction[1]:.3f}, {p1.gaze_direction[2]:.3f})",
            distance_3d=pairwise.distance_3d,
            closeness=pairwise.closeness_score,
            emotion_sim=pairwise.emotion_similarity,
            gaze_0_to_1=pairwise.gaze_intersects[0],
            gaze_1_to_0=pairwise.gaze_intersects[1],
            mutual_gaze=pairwise.mutual_gaze,
            dom0=pairwise.dominance_scores[0],
            dom1=pairwise.dominance_scores[1],
            dom_gap=pairwise.dominance_gap,
            engagement=pairwise.engagement_score,
            balance=pairwise.balance_index,
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            parsed = json.loads(content)

            return InteractionSummary(
                explanation=parsed.get("explanation", "Analysis could not be generated."),
                one_line_summary=parsed.get("one_line_summary", "No summary available."),
            )
        except Exception as e:
            return InteractionSummary(
                explanation=f"LLM interpretation unavailable: {str(e)}",
                one_line_summary="Interpretation service error.",
            )

    async def generate_voice_thoughts(
        self,
        image_bytes: bytes,
        image_ext: str,
        persons: list[PersonFeatures],
        pairwise: PairwiseFeatures,
        scene_explanation: str,
    ) -> list[dict]:
        """Generate scene-aware first-person thoughts for each person using GPT-4o vision."""
        image_b64 = base64.b64encode(image_bytes).decode()
        ext = image_ext.lower().replace("jpg", "jpeg")
        media_type = f"image/{ext}"

        prompt = VOICE_THOUGHT_PROMPT.format(
            scene_explanation=scene_explanation,
            dom0=pairwise.dominance_scores[0],
            dom1=pairwise.dominance_scores[1],
            engagement=pairwise.engagement_score,
            closeness=pairwise.closeness_score,
            mutual_gaze=pairwise.mutual_gaze,
            smile0=persons[0].smile_probability,
            smile1=persons[1].smile_probability,
        )

        try:
            response = await self.client.chat.completions.create(
                model=settings.openai_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:{media_type};base64,{image_b64}"},
                            },
                            {"type": "text", "text": prompt},
                        ],
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=300,
            )
            parsed = json.loads(response.choices[0].message.content)
            return [
                {
                    "person_id": 0,
                    "thought_text": parsed["person_0"]["thought"],
                    "tone": parsed["person_0"].get("tone", "warm"),
                },
                {
                    "person_id": 1,
                    "thought_text": parsed["person_1"]["thought"],
                    "tone": parsed["person_1"].get("tone", "warm"),
                },
            ]
        except Exception:
            return []

    def interpret_sync_fallback(
        self,
        persons: list[PersonFeatures],
        pairwise: PairwiseFeatures,
    ) -> InteractionSummary:
        """Generate a rule-based fallback interpretation without LLM."""
        sentences = []

        if pairwise.mutual_gaze:
            sentences.append(
                "Both individuals appear to be directing their gaze toward each other, "
                "suggesting mutual visual attention."
            )
        elif pairwise.gaze_intersects[0] and not pairwise.gaze_intersects[1]:
            sentences.append(
                "Person 0 appears to direct visual attention toward Person 1, "
                "while Person 1's gaze is directed elsewhere."
            )
        elif pairwise.gaze_intersects[1] and not pairwise.gaze_intersects[0]:
            sentences.append(
                "Person 1 appears to direct visual attention toward Person 0, "
                "while Person 0's gaze is directed elsewhere."
            )

        if pairwise.closeness_score > 0.6:
            sentences.append("The two individuals are positioned in close physical proximity.")
        elif pairwise.closeness_score < 0.3:
            sentences.append("The two individuals maintain considerable spatial distance.")

        if pairwise.dominance_gap > 0.3:
            dominant = 0 if pairwise.dominance_scores[0] > pairwise.dominance_scores[1] else 1
            sentences.append(
                f"Person {dominant} displays more visually expansive posture and higher "
                "perceived interaction presence."
            )

        if pairwise.emotion_similarity > 0.7:
            sentences.append(
                "Both individuals display similar levels of facial expressiveness."
            )

        if pairwise.engagement_score > 0.6:
            summary = "High perceived visual engagement between both individuals."
        elif pairwise.engagement_score > 0.3:
            summary = "Moderate perceived visual engagement observed."
        else:
            summary = "Low perceived visual engagement between the two individuals."

        if not sentences:
            sentences.append("The visual interaction signals are within neutral ranges.")

        return InteractionSummary(
            explanation=" ".join(sentences),
            one_line_summary=summary,
        )
