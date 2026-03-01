import type { DetectedPerson } from "../utils/api";

interface Props {
  imageUrl: string;
  persons: DetectedPerson[];
  selected: number[];
  onToggle: (personId: number) => void;
}

const COLORS = ["#6c63ff", "#ff6b6b", "#4caf50", "#ff9800", "#2196f3", "#e91e63"];

export default function ImageOverlay({ imageUrl, persons, selected, onToggle }: Props) {
  return (
    <div style={{ position: "relative", display: "inline-block", width: "100%" }}>
      <img
        src={imageUrl}
        alt="Detected persons"
        style={{
          width: "100%",
          maxHeight: 420,
          objectFit: "contain",
          display: "block",
          borderRadius: 8,
        }}
      />
      {/* SVG overlay — matches image natural size via viewBox 0 0 1 1 with preserveAspectRatio */}
      <svg
        viewBox="0 0 1 1"
        preserveAspectRatio="xMidYMid meet"
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          cursor: "pointer",
        }}
      >
        {persons.map((person) => {
          const [x1, y1, x2, y2] = person.bbox;
          const isSelected = selected.includes(person.person_id);
          const color = COLORS[person.person_id % COLORS.length];
          const boxW = x2 - x1;
          const boxH = y2 - y1;
          const labelSize = 0.035;

          return (
            <g
              key={person.person_id}
              onClick={() => onToggle(person.person_id)}
              style={{ cursor: "pointer" }}
            >
              {/* Bounding box */}
              <rect
                x={x1}
                y={y1}
                width={boxW}
                height={boxH}
                fill={isSelected ? `${color}22` : "transparent"}
                stroke={color}
                strokeWidth={isSelected ? 0.004 : 0.002}
                strokeDasharray={isSelected ? "none" : "0.01,0.005"}
                rx={0.005}
              />
              {/* Label badge background */}
              <rect
                x={x1}
                y={y1 - labelSize - 0.008}
                width={labelSize * 2.2}
                height={labelSize + 0.008}
                fill={isSelected ? color : `${color}99`}
                rx={0.004}
              />
              {/* Label text */}
              <text
                x={x1 + labelSize * 0.15}
                y={y1 - 0.005}
                fontSize={labelSize * 0.85}
                fill="white"
                fontWeight="bold"
                fontFamily="monospace"
              >
                P{person.person_id}
              </text>
              {/* Checkmark indicator when selected */}
              {isSelected && (
                <circle
                  cx={x2 - 0.02}
                  cy={y1 + 0.02}
                  r={0.018}
                  fill={color}
                />
              )}
              {isSelected && (
                <text
                  x={x2 - 0.028}
                  y={y1 + 0.027}
                  fontSize={0.022}
                  fill="white"
                  fontWeight="bold"
                >
                  ✓
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
}
