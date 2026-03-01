import { Canvas } from "@react-three/fiber";
import { OrbitControls, Text, Line } from "@react-three/drei";
import type { PersonFeatures, PairwiseFeatures } from "../utils/api";

interface Props {
  persons: PersonFeatures[];
  pairwise: PairwiseFeatures;
  imageUrl: string | null;
}

function PersonMarker({
  person,
  dominance,
  color,
  label,
}: {
  person: PersonFeatures;
  dominance: number;
  color: string;
  label: string;
}) {
  // Map normalized 2D coords to 3D scene coords
  const x = (person.center_2d[0] - 0.5) * 6;
  const y = -(person.center_2d[1] - 0.5) * 6;
  const z = (person.depth - 0.5) * 3;

  const scale = 0.3 + dominance * 0.4;

  // Gaze direction arrow
  const gx = person.gaze_direction[0] * 2;
  const gy = -person.gaze_direction[1] * 2;
  const gz = person.gaze_direction[2] * 2;

  return (
    <group position={[x, y, z]}>
      {/* Body sphere */}
      <mesh>
        <sphereGeometry args={[scale, 16, 16]} />
        <meshStandardMaterial color={color} transparent opacity={0.8} />
      </mesh>

      {/* Label */}
      <Text position={[0, scale + 0.3, 0]} fontSize={0.25} color="#ffffff">
        {label}
      </Text>

      {/* Gaze direction line */}
      <Line
        points={[
          [0, 0, 0],
          [gx, gy, gz],
        ]}
        color="#ffeb3b"
        lineWidth={2}
      />
    </group>
  );
}

function ConnectionLine({
  persons,
  pairwise,
}: {
  persons: PersonFeatures[];
  pairwise: PairwiseFeatures;
}) {
  const p0 = persons[0];
  const p1 = persons[1];

  const start: [number, number, number] = [
    (p0.center_2d[0] - 0.5) * 6,
    -(p0.center_2d[1] - 0.5) * 6,
    (p0.depth - 0.5) * 3,
  ];
  const end: [number, number, number] = [
    (p1.center_2d[0] - 0.5) * 6,
    -(p1.center_2d[1] - 0.5) * 6,
    (p1.depth - 0.5) * 3,
  ];

  const engColor = pairwise.engagement_score > 0.5 ? "#4caf50" : "#ff9800";

  return (
    <>
      <Line
        points={[start, end]}
        color={engColor}
        lineWidth={1 + pairwise.engagement_score * 4}
        dashed={!pairwise.mutual_gaze}
        dashSize={0.2}
        gapSize={0.1}
      />
      <Text
        position={[
          (start[0] + end[0]) / 2,
          (start[1] + end[1]) / 2 + 0.4,
          (start[2] + end[2]) / 2,
        ]}
        fontSize={0.2}
        color={engColor}
      >
        {`Eng: ${(pairwise.engagement_score * 100).toFixed(0)}%`}
      </Text>
    </>
  );
}

export default function InteractionVisualization({ persons, pairwise, imageUrl }: Props) {
  if (persons.length < 2) return null;

  return (
    <div
      style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius)",
        border: "1px solid var(--border)",
        overflow: "hidden",
      }}
    >
      <h3
        style={{
          fontSize: "0.95rem",
          fontWeight: 600,
          padding: "1rem 1.25rem 0",
          color: "var(--accent)",
        }}
      >
        3D Interaction Visualization
      </h3>
      <div style={{ height: 400 }}>
        <Canvas camera={{ position: [0, 0, 8], fov: 50 }}>
          <ambientLight intensity={0.6} />
          <directionalLight position={[5, 5, 5]} intensity={0.8} />

          <PersonMarker
            person={persons[0]}
            dominance={pairwise.dominance_scores[0]}
            color="#6c63ff"
            label="Person 0"
          />
          <PersonMarker
            person={persons[1]}
            dominance={pairwise.dominance_scores[1]}
            color="#e91e63"
            label="Person 1"
          />
          <ConnectionLine persons={persons} pairwise={pairwise} />

          {/* Ground grid */}
          <gridHelper args={[10, 10, "#2d3148", "#2d3148"]} position={[0, -3, 0]} />

          <OrbitControls enableDamping dampingFactor={0.1} />
        </Canvas>
      </div>
    </div>
  );
}
