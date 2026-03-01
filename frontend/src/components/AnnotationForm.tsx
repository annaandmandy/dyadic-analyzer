import { useState } from "react";
import { submitAnnotation } from "../utils/api";

interface Props {
  imageId: string;
}

export default function AnnotationForm({ imageId }: Props) {
  const [dominant, setDominant] = useState(0);
  const [strength, setStrength] = useState(3);
  const [mutual, setMutual] = useState(true);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    try {
      await submitAnnotation({
        image_id: imageId,
        dominant_person: dominant,
        interaction_strength: strength,
        mutual_attention: mutual,
      });
      setSubmitted(true);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (submitted) {
    return (
      <div
        style={{
          background: "var(--bg-card)",
          borderRadius: "var(--radius)",
          padding: "1.25rem",
          border: "1px solid var(--success)",
          textAlign: "center",
          color: "var(--success)",
        }}
      >
        Annotation submitted. Thank you!
        <br />
        <button
          onClick={() => setSubmitted(false)}
          style={{
            marginTop: 8,
            padding: "0.3rem 0.8rem",
            background: "transparent",
            color: "var(--accent)",
            border: "1px solid var(--accent)",
            borderRadius: 6,
            fontSize: "0.8rem",
          }}
        >
          Submit another
        </button>
      </div>
    );
  }

  return (
    <div
      style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius)",
        padding: "1.25rem",
        border: "1px solid var(--border)",
      }}
    >
      <h3 style={{ fontSize: "0.95rem", fontWeight: 600, marginBottom: "1rem", color: "var(--accent)" }}>
        Human Annotation
      </h3>

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.85rem", display: "block", marginBottom: 6 }}>
          Who appears more dominant in the interaction?
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          {[0, 1].map((p) => (
            <button
              key={p}
              onClick={() => setDominant(p)}
              style={{
                padding: "0.4rem 1rem",
                borderRadius: 6,
                background: dominant === p ? "var(--accent)" : "var(--bg-secondary)",
                color: dominant === p ? "#fff" : "var(--text-primary)",
                border: `1px solid ${dominant === p ? "var(--accent)" : "var(--border)"}`,
                fontSize: "0.85rem",
              }}
            >
              Person {p}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.85rem", display: "block", marginBottom: 6 }}>
          Rate interaction strength (1-5):
        </label>
        <div style={{ display: "flex", gap: 6 }}>
          {[1, 2, 3, 4, 5].map((v) => (
            <button
              key={v}
              onClick={() => setStrength(v)}
              style={{
                width: 36,
                height: 36,
                borderRadius: 6,
                background: strength === v ? "var(--accent)" : "var(--bg-secondary)",
                color: strength === v ? "#fff" : "var(--text-primary)",
                border: `1px solid ${strength === v ? "var(--accent)" : "var(--border)"}`,
                fontSize: "0.9rem",
                fontWeight: 600,
              }}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: "1rem" }}>
        <label style={{ fontSize: "0.85rem", display: "block", marginBottom: 6 }}>
          Are both mutually attentive?
        </label>
        <div style={{ display: "flex", gap: 8 }}>
          {[true, false].map((v) => (
            <button
              key={String(v)}
              onClick={() => setMutual(v)}
              style={{
                padding: "0.4rem 1rem",
                borderRadius: 6,
                background: mutual === v ? "var(--accent)" : "var(--bg-secondary)",
                color: mutual === v ? "#fff" : "var(--text-primary)",
                border: `1px solid ${mutual === v ? "var(--accent)" : "var(--border)"}`,
                fontSize: "0.85rem",
              }}
            >
              {v ? "Yes" : "No"}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <p style={{ color: "var(--danger)", fontSize: "0.85rem", marginBottom: 8 }}>{error}</p>
      )}

      <button
        onClick={handleSubmit}
        style={{
          width: "100%",
          padding: "0.6rem",
          background: "var(--accent)",
          color: "#fff",
          borderRadius: 8,
          fontWeight: 600,
          fontSize: "0.9rem",
        }}
      >
        Submit Annotation
      </button>
    </div>
  );
}
