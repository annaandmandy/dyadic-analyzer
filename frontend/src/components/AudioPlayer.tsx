import { useState, useRef } from "react";
import type { VoiceThought } from "../utils/api";

interface Props {
  voiceThoughts: VoiceThought[];
}

const TONE_COLORS: Record<string, string> = {
  confident: "#e91e63",
  warm: "#ff9800",
  reserved: "#607d8b",
};

export default function AudioPlayer({ voiceThoughts }: Props) {
  const [playing, setPlaying] = useState<number | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  if (!voiceThoughts.length) return null;

  const playAudio = async (idx: number) => {
    const thought = voiceThoughts[idx];
    if (!thought.audio_url) return;

    if (audioRef.current) {
      audioRef.current.pause();
    }

    const audio = new Audio(thought.audio_url);
    audioRef.current = audio;
    setPlaying(idx);

    audio.onended = () => {
      setPlaying(null);
      // Auto-play next if available
      if (idx + 1 < voiceThoughts.length && voiceThoughts[idx + 1].audio_url) {
        playAudio(idx + 1);
      }
    };

    audio.play().catch(() => setPlaying(null));
  };

  const stop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    setPlaying(null);
  };

  return (
    <div
      style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius)",
        padding: "1.25rem",
        border: "1px solid var(--border)",
        marginBottom: "1rem",
      }}
    >
      <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "1rem", color: "var(--accent)" }}>
        Simulated Internal Thoughts
      </h3>

      {voiceThoughts.map((thought, i) => (
        <div
          key={i}
          style={{
            padding: "0.75rem",
            marginBottom: "0.5rem",
            background: "var(--bg-secondary)",
            borderRadius: 8,
            borderLeft: `3px solid ${TONE_COLORS[thought.tone] || "var(--accent)"}`,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
                Person {thought.person_id} ({thought.tone})
              </span>
              <p style={{ marginTop: 4, fontSize: "0.9rem", fontStyle: "italic" }}>
                "{thought.thought_text}"
              </p>
            </div>
            {thought.audio_url && (
              <button
                onClick={() => (playing === i ? stop() : playAudio(i))}
                style={{
                  padding: "0.4rem 0.8rem",
                  background: playing === i ? "var(--danger)" : "var(--accent)",
                  color: "#fff",
                  borderRadius: 6,
                  fontSize: "0.8rem",
                  flexShrink: 0,
                  marginLeft: 12,
                }}
              >
                {playing === i ? "Stop" : "Play"}
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
