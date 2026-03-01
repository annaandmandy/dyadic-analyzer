"""Voice simulation using ElevenLabs TTS."""

import os
import uuid
import httpx

from app.config import settings
from app.models.schemas import PairwiseFeatures, PersonFeatures, VoiceThought

ELEVENLABS_API_URL = "https://api.elevenlabs.io/v1/text-to-speech"


class VoiceSimulator:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        os.makedirs(settings.audio_dir, exist_ok=True)

    def determine_tone(
        self, person: PersonFeatures, pairwise: PairwiseFeatures, person_idx: int
    ) -> str:
        """Determine voice tone based on scores."""
        dom_score = pairwise.dominance_scores[person_idx]
        other_dom = pairwise.dominance_scores[1 - person_idx]

        if dom_score > other_dom + 0.15:
            return "confident"
        elif pairwise.engagement_score > 0.5:
            return "warm"
        elif pairwise.balance_index < 0.4:
            return "reserved"
        else:
            return "warm"

    def generate_thought(
        self, person: PersonFeatures, pairwise: PairwiseFeatures, person_idx: int
    ) -> str:
        """Rule-based fallback thought when LLM is unavailable."""
        tone = self.determine_tone(person, pairwise, person_idx)
        engagement = pairwise.engagement_score

        if tone == "confident":
            if engagement > 0.5:
                return "I feel like we're really connecting right now."
            return "I'm comfortable taking the lead in this moment."
        elif tone == "warm":
            if pairwise.mutual_gaze:
                return "It's nice to share this moment of attention together."
            return "I sense a gentle ease in how we're standing together."
        else:  # reserved
            if pairwise.gaze_intersects[person_idx]:
                return "I'm watching, though I'm holding back a bit."
            return "I'm present but keeping a quiet distance for now."

    def _select_voice_id(
        self, tone: str, perceived_gender: str = "neutral", energy: str = "medium"
    ) -> str:
        """Select ElevenLabs voice based on perceived gender and energy level."""
        gender = perceived_gender.lower()
        if gender == "male":
            return {
                "high": settings.elevenlabs_voice_male_high,
                "medium": settings.elevenlabs_voice_male_medium,
                "low": settings.elevenlabs_voice_male_low,
            }.get(energy, settings.elevenlabs_voice_male_medium)
        elif gender == "female":
            return {
                "high": settings.elevenlabs_voice_female_high,
                "medium": settings.elevenlabs_voice_female_medium,
                "low": settings.elevenlabs_voice_female_low,
            }.get(energy, settings.elevenlabs_voice_female_medium)
        else:
            # Tone-based fallback when gender is unknown
            return {
                "confident": settings.elevenlabs_voice_male_medium,
                "warm": settings.elevenlabs_voice_female_medium,
                "reserved": settings.elevenlabs_voice_male_low,
            }.get(tone, settings.elevenlabs_voice_female_medium)

    async def synthesize(
        self,
        text: str,
        tone: str,
        person_idx: int,
        perceived_gender: str = "neutral",
        energy: str = "medium",
    ) -> str | None:
        """Call ElevenLabs API and save audio. Returns relative audio path."""
        if not self.api_key:
            return None

        voice_id = self._select_voice_id(tone, perceived_gender, energy)
        url = f"{ELEVENLABS_API_URL}/{voice_id}"

        # Voice stability: higher energy = more expressive (lower stability)
        stability = {"high": 0.35, "medium": 0.5, "low": 0.7}.get(energy, 0.5)
        similarity_boost = {"high": 0.85, "medium": 0.75, "low": 0.6}.get(energy, 0.75)

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()

                filename = f"person_{person_idx}_{uuid.uuid4().hex[:8]}.mp3"
                filepath = os.path.join(settings.audio_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(response.content)

                return f"/api/audio/{filename}"
        except Exception:
            return None

    async def process_both(
        self,
        persons: list[PersonFeatures],
        pairwise: PairwiseFeatures,
        pregenerated_thoughts: list[dict] | None = None,
        generate_audio: bool = True,
    ) -> list[VoiceThought]:
        """Generate thoughts and audio for both persons."""
        results = []
        for i, person in enumerate(persons):
            if pregenerated_thoughts and i < len(pregenerated_thoughts):
                t = pregenerated_thoughts[i]
                tone = t["tone"]
                thought = t["thought_text"]
                perceived_gender = t.get("perceived_gender", "neutral")
                energy = t.get("energy", "medium")
            else:
                tone = self.determine_tone(person, pairwise, i)
                thought = self.generate_thought(person, pairwise, i)
                perceived_gender = "neutral"
                energy = "medium"

            audio_url = (
                await self.synthesize(thought, tone, i, perceived_gender, energy)
                if generate_audio
                else None
            )

            results.append(VoiceThought(
                person_id=i,
                thought_text=thought,
                tone=tone,
                audio_url=audio_url,
            ))

        return results
