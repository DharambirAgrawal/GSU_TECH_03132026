import { useState } from "react";
import React from "react";

const mockData = {
  percent: 78,
  reasons: [
    "Most data entries were verified and accurate.",
    "Minor discrepancies found in 2% of records.",
    "No critical errors detected.",
    "Recent updates improved overall accuracy.",
  ],
};

// Simple mock data for the chart
const accuracyHistory = [
  { date: "2026-01-01", value: 68 },
  { date: "2026-01-15", value: 70 },
  { date: "2026-02-01", value: 72 },
  { date: "2026-02-15", value: 75 },
  { date: "2026-03-01", value: 78 },
];

function AccuracyChart({ data }) {
  // SVG chart dimensions
  const width = 340;
  const height = 120;
  const padding = 32;
  const maxVal = Math.max(...data.map(d => d.value), 100);
  const minVal = Math.min(...data.map(d => d.value), 0);
  const points = data.map((d, i) => [
    padding + (i * (width - 2 * padding)) / (data.length - 1),
    height - padding - ((d.value - minVal) / (maxVal - minVal)) * (height - 2 * padding)
  ]);

  // Bar width
  const barW = (width - 2 * padding) / data.length - 6;

  return (
    <div style={{ marginTop: 36, background: '#fff', borderRadius: 12, boxShadow: '0 1px 4px #6366f11a', padding: 18 }}>
      <div style={{ fontWeight: 700, color: '#8219a2', marginBottom: 8 }}>AI Accuracy Over Time</div>
      <svg width={width} height={height} style={{ width: '100%', maxWidth: 420, display: 'block' }}>
        {/* Bars */}
        {data.map((d, i) => (
          <rect
            key={d.date}
            x={padding + i * (width - 2 * padding) / (data.length - 1) - barW / 2}
            y={height - padding - ((d.value - minVal) / (maxVal - minVal)) * (height - 2 * padding)}
            width={barW}
            height={((d.value - minVal) / (maxVal - minVal)) * (height - 2 * padding)}
            fill="#a5b4fc"
            rx={3}
          />
        ))}
        {/* Line */}
        <polyline
          fill="none"
          stroke="#6366f1"
          strokeWidth={3}
          points={points.map(p => p.join(",")).join(" ")}
        />
        {/* Dots */}
        {points.map(([x, y], i) => (
          <circle key={i} cx={x} cy={y} r={4} fill="#6366f1" stroke="#fff" strokeWidth={2} />
        ))}
        {/* X axis labels */}
        {data.map((d, i) => (
          <text
            key={d.date}
            x={padding + i * (width - 2 * padding) / (data.length - 1)}
            y={height - 8}
            textAnchor="middle"
            fontSize={11}
            fill="#64748b"
          >
            {d.date.slice(5)}
          </text>
        ))}
        {/* Y axis labels */}
        <text x={8} y={height - padding} fontSize={11} fill="#64748b">{minVal}%</text>
        <text x={8} y={padding} fontSize={11} fill="#64748b">{maxVal}%</text>
      </svg>
    </div>
  );
}

export default function AccuracyPage() {
  const [data] = useState(mockData);

  return (
    <div className="accuracy-page-header" style={{ maxWidth: 520, margin: '0 auto', padding: '2rem 1.5rem' }}>
      <h1 style={{ textAlign: 'center', fontSize: 32, fontWeight: 800, color: '#8219a2', marginBottom: 6 }}>Accuracy Overview</h1>
      <p className="text-gray-500 mb-6" style={{ textAlign: 'center', fontSize: 16 }}>Summary of data accuracy and key findings.</p>
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 32 }}>
        <div style={{
          background: '#f1f5f9',
          borderRadius: 18,
          boxShadow: '0 2px 12px #6366f11a',
          padding: '36px 44px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          minWidth: 120,
        }}>
          <div style={{ fontSize: 64, fontWeight: 900, color: '#8219a2', lineHeight: 1 }}>{data.percent}%</div>
          <div style={{ fontSize: 16, color: '#334155', marginTop: 8 }}>Overall Data Accuracy</div>
        </div>
      </div>
      <div className="bg-gray-50 rounded p-6" style={{ marginTop: 12 }}>
        <div className="font-semibold text-gray-800 mb-2" style={{ fontSize: 17 }}>Key Points:</div>
        <ul className="list-disc ml-6 text-gray-700" style={{ fontSize: 15 }}>
          {data.reasons.map((reason, i) => (
            <li key={i}>{reason}</li>
          ))}
        </ul>
      </div>
      <AccuracyChart data={accuracyHistory} />
    </div>
  );
}
