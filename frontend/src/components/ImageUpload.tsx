import { useState, useRef } from "react";
import { analyzeImage, detectPersons, type AnalysisResult, type GroupDetectionResult } from "../utils/api";
import ImageOverlay from "./ImageOverlay";

interface Props {
  onResult: (result: AnalysisResult, imageUrl: string) => void;
  onLoading: (loading: boolean) => void;
  onError: (error: string) => void;
}

// Step 1: waiting for file / Step 2: persons detected, selecting pair / Step 3: analyzing
type Step = "upload" | "select" | "done";

export default function ImageUpload({ onResult, onLoading, onError }: Props) {
  const [dragOver, setDragOver] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);
  const [useLlm, setUseLlm] = useState(true);
  const [generateAudio, setGenerateAudio] = useState(true);
  const [step, setStep] = useState<Step>("upload");
  const [detection, setDetection] = useState<GroupDetectionResult | null>(null);
  const [selected, setSelected] = useState<number[]>([]);
  const [detecting, setDetecting] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const fileObjRef = useRef<File | null>(null);

  const handleFile = (file: File) => {
    if (!file.type.startsWith("image/")) {
      onError("Please upload an image file (JPEG, PNG, or WebP).");
      return;
    }
    fileObjRef.current = file;
    setPreview(URL.createObjectURL(file));
    setDetection(null);
    setSelected([]);
    setStep("upload");
  };

  const handleDetect = async () => {
    const file = fileObjRef.current;
    if (!file) return;
    setDetecting(true);
    onError("");
    try {
      const result = await detectPersons(file);
      setDetection(result);
      // Auto-select if exactly 2 people
      const ids = result.persons.map((p) => p.person_id);
      setSelected(ids.length === 2 ? ids : []);
      setStep("select");
    } catch (e: any) {
      onError(e.message || "Detection failed");
    } finally {
      setDetecting(false);
    }
  };

  const handleToggle = (personId: number) => {
    setSelected((prev) => {
      if (prev.includes(personId)) {
        return prev.filter((id) => id !== personId);
      }
      if (prev.length >= 2) {
        // Replace the oldest selection with the new one
        return [prev[1], personId];
      }
      return [...prev, personId];
    });
  };

  const handleAnalyze = async () => {
    const file = fileObjRef.current;
    if (!file || selected.length !== 2) return;

    const [p0, p1] = selected.sort((a, b) => a - b);
    onLoading(true);
    try {
      const result = await analyzeImage(file, {
        useLlm,
        generateAudio,
        person0: p0,
        person1: p1,
      });
      setStep("done");
      onResult(result, preview!);
    } catch (e: any) {
      onError(e.message || "Analysis failed");
    } finally {
      onLoading(false);
    }
  };

  return (
    <div style={{ marginBottom: "1.5rem" }}>
      {/* Drop zone — always visible so user can swap image */}
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
        onClick={() => step === "upload" && fileRef.current?.click()}
        style={{
          border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border)"}`,
          borderRadius: "var(--radius)",
          padding: step === "upload" ? "2rem" : "0.75rem",
          textAlign: "center",
          cursor: step === "upload" ? "pointer" : "default",
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

        {step === "upload" && !preview && (
          <div>
            <p style={{ fontSize: "1.1rem", color: "var(--text-primary)" }}>
              Drop an image here or click to upload
            </p>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginTop: 4 }}>
              Works with 2 or more people — you'll choose which pair to analyze
            </p>
          </div>
        )}

        {step === "upload" && preview && (
          <img
            src={preview}
            alt="Preview"
            style={{ maxHeight: 300, maxWidth: "100%", borderRadius: 8, objectFit: "contain" }}
          />
        )}

        {(step === "select" || step === "done") && preview && detection && (
          <ImageOverlay
            imageUrl={preview}
            persons={detection.persons}
            selected={selected}
            onToggle={step === "select" ? handleToggle : () => {}}
          />
        )}
      </div>

      {/* Step 1: after file picked, show Detect button */}
      {step === "upload" && preview && (
        <div style={{ marginTop: "1rem", display: "flex", justifyContent: "flex-end" }}>
          <button
            onClick={handleDetect}
            disabled={detecting}
            style={{
              padding: "0.6rem 1.5rem",
              background: "var(--accent)",
              color: "#fff",
              borderRadius: 8,
              fontWeight: 600,
              fontSize: "0.95rem",
              opacity: detecting ? 0.6 : 1,
            }}
          >
            {detecting ? "Detecting…" : "Detect People"}
          </button>
        </div>
      )}

      {/* Step 2: person selection + analyze controls */}
      {step === "select" && detection && (
        <div style={{ marginTop: "1rem" }}>
          <p style={{ fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "0.75rem" }}>
            {detection.persons.length === 2
              ? "Both people auto-selected. Click Analyze to continue, or click a box to change selection."
              : `${detection.persons.length} people detected. Click 2 to select (selected: ${selected.length}/2).`}
          </p>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "1rem",
              flexWrap: "wrap",
            }}
          >
            <label style={{ display: "flex", alignItems: "center", gap: 6, fontSize: "0.9rem" }}>
              <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
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
            <div style={{ display: "flex", gap: "0.5rem", marginLeft: "auto" }}>
              <button
                onClick={() => {
                  setStep("upload");
                  setDetection(null);
                  setSelected([]);
                  fileRef.current?.click();
                }}
                style={{
                  padding: "0.6rem 1rem",
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  color: "var(--text-secondary)",
                  borderRadius: 8,
                  fontSize: "0.9rem",
                }}
              >
                Change Image
              </button>
              <button
                onClick={handleAnalyze}
                disabled={selected.length !== 2}
                style={{
                  padding: "0.6rem 1.5rem",
                  background: selected.length === 2 ? "var(--accent)" : "var(--border)",
                  color: "#fff",
                  borderRadius: 8,
                  fontWeight: 600,
                  fontSize: "0.95rem",
                  cursor: selected.length === 2 ? "pointer" : "not-allowed",
                }}
              >
                Analyze Selected ({selected.length}/2)
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Step done: show re-analyze option */}
      {step === "done" && (
        <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem", justifyContent: "flex-end" }}>
          <button
            onClick={() => setStep("select")}
            style={{
              padding: "0.5rem 1rem",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              borderRadius: 8,
              fontSize: "0.85rem",
            }}
          >
            Change Selection
          </button>
          <button
            onClick={() => {
              setStep("upload");
              setDetection(null);
              setSelected([]);
              setPreview(null);
              fileObjRef.current = null;
              fileRef.current?.click();
            }}
            style={{
              padding: "0.5rem 1rem",
              background: "var(--bg-card)",
              border: "1px solid var(--border)",
              color: "var(--text-secondary)",
              borderRadius: 8,
              fontSize: "0.85rem",
            }}
          >
            Upload New Image
          </button>
        </div>
      )}
    </div>
  );
}
