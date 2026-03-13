import { useState, useEffect } from "react";

const mockCompetitors = [
  { name: "Acme Corp", score: 92, marketShare: 28, trend: "+2%" },
  { name: "Globex Inc", score: 87, marketShare: 24, trend: "-1%" },
  { name: "Umbrella LLC", score: 80, marketShare: 18, trend: "+0.5%" },
  { name: "Initech", score: 75, marketShare: 15, trend: "+1%" },
  { name: "Hooli", score: 70, marketShare: 10, trend: "-0.5%" },
];

// MetricCard component
function MetricCard({ label, value, sub }) {
  return (
    <div style={{
      background: '#f1f5f9',
      borderRadius: 10,
      padding: '18px 14px',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'flex-start',
      minWidth: 0,
      boxShadow: '0 1px 4px rgba(30,64,175,0.04)'
    }}>
      <div style={{ fontSize: 13, color: '#64748b', fontWeight: 600, marginBottom: 2 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: '#1e293b', marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 12, color: '#64748b' }}>{sub}</div>
    </div>
  );
}

// ScoreBar component
function ScoreBar({ score, max }) {
  const percent = max ? Math.round((score / max) * 100) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{ width: 60, height: 8, background: '#e5e7eb', borderRadius: 4, overflow: 'hidden', marginRight: 6 }}>
        <div style={{ width: `${percent}%`, height: '100%', background: '#6366f1', borderRadius: 4, transition: 'width 0.3s' }} />
      </div>
      <span style={{ fontWeight: 600, color: '#334155', fontSize: 13 }}>{score}</span>
    </div>
  );
}

// TrendBadge component
function TrendBadge({ trend }) {
  const isPositive = trend.startsWith('+');
  const isNegative = trend.startsWith('-');
  return (
    <span style={{
      display: 'inline-block',
      background: isPositive ? '#dcfce7' : isNegative ? '#fee2e2' : '#f3f4f6',
      color: isPositive ? '#15803d' : isNegative ? '#b91c1c' : '#64748b',
      fontWeight: 700,
      fontSize: 13,
      borderRadius: 6,
      padding: '2px 10px',
      minWidth: 36,
      textAlign: 'center',
    }}>{trend}</span>
  );
}

// MarketShareChart component (simple bar chart)
function MarketShareChart({ competitors }) {
  const total = competitors.reduce((sum, c) => sum + c.marketShare, 0);
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 60, background: '#f9fafb', borderRadius: 8, padding: '12px 10px' }}>
      {competitors.map((c, i) => {
        const percent = total ? (c.marketShare / total) * 100 : 0;
        return (
          <div key={c.name} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <div style={{
              height: `${percent * 0.5 + 10}px`,
              width: 18,
              background: i === 0 ? '#6366f1' : '#a5b4fc',
              borderRadius: 6,
              marginBottom: 4,
              transition: 'height 0.3s',
            }} />
            <span style={{ fontSize: 11, color: '#64748b', fontWeight: 600 }}>{c.name.split(' ')[0]}</span>
          </div>
        );
      })}
    </div>
  );
}

export default function CompetitorsPage() {
  const [competitors, setCompetitors] = useState([]);

  useEffect(() => {
    setTimeout(() => setCompetitors(mockCompetitors), 500);
  }, []);

  // Calculate comparative insights
  const topCompetitor = competitors[0];
  const avgScore = competitors.length
    ? (competitors.reduce((sum, c) => sum + c.score, 0) / competitors.length).toFixed(1)
    : 0;

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-2">Top Competitors</h1>
      <p className="text-gray-500 mb-6">Comparative insights based on latest data.</p>
      <div className="overflow-x-auto rounded shadow bg-white">
        <table className="min-w-full text-left">
          <thead>
            <tr className="bg-gray-100">
              <th className="py-2 px-4">Name</th>
              <th className="py-2 px-4">Score</th>
              <th className="py-2 px-4">Market Share (%)</th>
              <th className="py-2 px-4">Trend</th>
            </tr>
          </thead>
          <tbody>
            {competitors.map((c, i) => (
              <tr key={c.name} className={i === 0 ? "bg-indigo-50 font-semibold" : ""}>
                <td className="py-2 px-4">{c.name}</td>
                <td className="py-2 px-4">
                  <ScoreBar score={c.score} max={100} />
                </td>
                <td className="py-2 px-4">{c.marketShare}</td>
                <td className="py-2 px-4">
                  <TrendBadge trend={c.trend} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <MetricCard
          label="Top Competitor"
          value={topCompetitor ? topCompetitor.name : "-"}
          sub={`Score: ${topCompetitor ? topCompetitor.score : "-"}`}
        />
        <MetricCard
          label="Average Score"
          value={avgScore}
          sub={`Across ${competitors.length} competitors`}
        />
      </div>
      <div className="mt-8">
        <h2 className="text-lg font-bold mb-2">Market Share</h2>
        <MarketShareChart competitors={competitors} />
      </div>
    </div>
  );
}
