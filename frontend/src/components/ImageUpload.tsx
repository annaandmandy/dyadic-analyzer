import { useState, useRef } from "react";
import { analyzeImage, type AnalysisResult } from "../utils/api";

interface Props {
  onResult: (result: AnalysisResult, imageUrl: string) => void;
  onLoading: (loading: boolean) => void;
  onError: (error: string) => void;
}

export default function ImageUpload({ onResult, onLoading, onError }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [useLlm, setUseLlm] = useState(true);
  const [generateAudio, setGenerateAudio] = useState(true);
  const fileRef = useRef<HTMLInputElement>(null);
  const fileObjRef = useRef<File | null>(null);

  const handleFile = (file: File) => {
    if (!file.type.startsWith("image/")) {
      onError("Please upload an image file (JPEG, PNG, or WebP).");
      return;
    }
    fileObjRef.current = file;
    setPreview(URL.createObjectURL(file));
  };

  const handleAnalyze = async () => {
    const file = fileObjRef.current;
    if (!file) return;

    onLoading(true);
    try {
      const result = await analyzeImage(file, { useLlm, generateAudio });
      onResult(result, preview!);
    } catch (e: any) {
      onError(e.message || "Analysis failed");
    } finally {
      onLoading(false);
    }
  };

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          const f = e.dataTransfer.files[0];
          if (f) handleFile(f);
        }}
        onClick={() => fileRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border)"}`,
          borderRadius: "var(--radius)",
          padding: "2rem",
          textAlign: "center",
          cursor: "pointer",
          background: dragOver ? "var(--accent-glow)" : "var(--bg-secondary)",
          transition: "all 0.2s",
        }}
      >
        <input
          ref={fileRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) handleFile(f);
          }}
        />
        {preview ? (
          <img
            src={preview}
            alt="Preview"
            style={{
              maxHeight: 300,
              maxWidth: "100%",
              borderRadius: 8,
              objectFit: "contain",
            }}
          />
        ) : (
          <div>
            <p style={{ fontSize: "1.1rem", color: "var(--text-primary)" }}>
              Drop an image here or click to upload
            </p>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginTop: 4 }}>
              Image must contain exactly two people
            </p>
          </div>
        )}
      </div>

      {preview && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "1rem",
            marginTop: "1rem",
            flexWrap: "wrap",
          }}
        >
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.9rem" }}>
            <input
              type="checkbox"
              checked={useLlm}
              onChange={(e) => setUseLlm(e.target.checked)}
            />
            LLM interpretation
          </label>
          <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.9rem" }}>
            <input
              type="checkbox"
              checked={generateAudio}
              onChange={(e) => setGenerateAudio(e.target.checked)}
            />
            Generate voice audio
          </label>
          <button
            onClick={handleAnalyze}
            style={{
              marginLeft: "auto",
              padding: "0.6rem 1.5rem",
              background: "var(--accent)",
              color: "#fff",
              borderRadius: 8,
              fontWeight: 600,
              fontSize: "0.95rem",
            }}
          >
            Analyze Image
          </button>
        </div>
      )}
    </div>
  );
}
