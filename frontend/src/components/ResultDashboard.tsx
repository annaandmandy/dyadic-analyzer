import type { AnalysisResult } from "../utils/api";

interface Props {
  result: AnalysisResult;
}

function ScoreBar({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ marginBottom: "0.75rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.85rem", marginBottom: 4 }}>
        <span>{label}</span>
        <span style={{ color: "var(--text-secondary)" }}>{(value * 100).toFixed(1)}%</span>
      </div>
      <div style={{ height: 8, background: "var(--bg-primary)", borderRadius: 4, overflow: "hidden" }}>
        <div
          style={{
            height: "100%",
            width: `${Math.min(value * 100, 100)}%`,
            background: color,
            borderRadius: 4,
            transition: "width 0.5s ease",
          }}
        />
      </div>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div
      style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius)",
        padding: "1.25rem",
        border: "1px solid var(--border)",
      }}
    >
      <h3
        style={{
          fontSize: "0.95rem",
          fontWeight: 600,
          marginBottom: "1rem",
          color: "var(--accent)",
        }}
      >
        {title}
      </h3>
      {children}
    </div>
  );
}

export default function ResultDashboard({ result }: Props) {
  const { pairwise, interpretation, persons } = result;

  return (
    <div>
      {/* Summary */}
      <div
        style={{
          background: "var(--bg-card)",
          borderRadius: "var(--radius)",
          padding: "1.25rem",
          border: "1px solid var(--border)",
          marginBottom: "1.5rem",
        }}
      >
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>
          {interpretation.one_line_summary}
        </h3>
        <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", lineHeight: 1.7 }}>
          {interpretation.explanation}
        </p>
      </div>

      {/* Score Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
          gap: "1rem",
        }}
      >
        <Card title="Dyad Metrics">
          <ScoreBar label="Engagement" value={pairwise.engagement_score} color="var(--accent)" />
          <ScoreBar label="Closeness" value={pairwise.closeness_score} color="#4caf50" />
          <ScoreBar label="Emotion Similarity" value={pairwise.emotion_similarity} color="#ff9800" />
          <ScoreBar label="Balance" value={pairwise.balance_index} color="#2196f3" />
          <div style={{ fontSize: "0.85rem", marginTop: 8, color: "var(--text-secondary)" }}>
            Mutual gaze: <strong>{pairwise.mutual_gaze ? "Yes" : "No"}</strong>
          </div>
        </Card>

        <Card title="Person 0">
          <ScoreBar
            label="Dominance"
            value={pairwise.dominance_scores[0]}
            color="#e91e63"
          />
          <ScoreBar
            label="Expansion"
            value={pairwise.expansion_scores[0]}
            color="#9c27b0"
          />
          <ScoreBar
            label="Smile"
            value={persons[0].smile_probability}
            color="#ff9800"
          />
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Yaw: {persons[0].face_yaw_angle.toFixed(1)} | Depth: {persons[0].depth.toFixed(3)}
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Gaze at other: {pairwise.gaze_intersects[0] ? "Yes" : "No"}
          </div>
        </Card>

        <Card title="Person 1">
          <ScoreBar
            label="Dominance"
            value={pairwise.dominance_scores[1]}
            color="#e91e63"
          />
          <ScoreBar
            label="Expansion"
            value={pairwise.expansion_scores[1]}
            color="#9c27b0"
          />
          <ScoreBar
            label="Smile"
            value={persons[1].smile_probability}
            color="#ff9800"
          />
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Yaw: {persons[1].face_yaw_angle.toFixed(1)} | Depth: {persons[1].depth.toFixed(3)}
          </div>
          <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
            Gaze at other: {pairwise.gaze_intersects[1] ? "Yes" : "No"}
          </div>
        </Card>
      </div>
    </div>
  );
}
