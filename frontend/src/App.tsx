import { useState } from "react";
import ImageUpload from "./components/ImageUpload";
import ResultDashboard from "./components/ResultDashboard";
import InteractionVisualization from "./components/InteractionVisualization";
import AudioPlayer from "./components/AudioPlayer";
import AnnotationForm from "./components/AnnotationForm";
import Disclaimer from "./components/Disclaimer";
import type { AnalysisResult } from "./utils/api";

export default function App() {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <div style={{ maxWidth: 1200, margin: "0 auto", padding: "2rem 1rem" }}>
      <header style={{ textAlign: "center", marginBottom: "2rem" }}>
        <h1
          style={{
            fontSize: "1.8rem",
            fontWeight: 700,
            background: "linear-gradient(135deg, var(--accent), #a78bfa)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Dyadic Visual Social Signal Analyzer
        </h1>
        <p style={{ color: "var(--text-secondary)", marginTop: "0.5rem" }}>
          Perceived visual interaction pattern analysis from a single image
        </p>
      </header>

      <Disclaimer />

      <ImageUpload
        onResult={(r, url) => {
          setResult(r);
          setImageUrl(url);
          setError(null);
        }}
        onLoading={setLoading}
        onError={(e) => {
          setError(e || null);
          if (e) setResult(null);
        }}
      />

      {loading && (
        <div style={{ textAlign: "center", padding: "3rem 0" }}>
          <div className="spinner" />
          <p style={{ color: "var(--text-secondary)", marginTop: "1rem" }}>
            Analyzing visual interaction signals...
          </p>
        </div>
      )}

      {error && (
        <div
          style={{
            background: "rgba(244, 67, 54, 0.1)",
            border: "1px solid var(--danger)",
            borderRadius: "var(--radius)",
            padding: "1rem",
            margin: "1rem 0",
            color: "var(--danger)",
          }}
        >
          {error}
        </div>
      )}

      {result && (
        <>
          <ResultDashboard result={result} />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "1.5rem",
              marginTop: "1.5rem",
            }}
          >
            <InteractionVisualization
              persons={result.persons}
              pairwise={result.pairwise}
              imageUrl={imageUrl}
            />
            <div>
              <AudioPlayer voiceThoughts={result.voice_thoughts} />
              <AnnotationForm imageId={result.image_id} />
            </div>
          </div>
        </>
      )}

      <style>{`
        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid var(--border);
          border-top-color: var(--accent);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          margin: 0 auto;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
