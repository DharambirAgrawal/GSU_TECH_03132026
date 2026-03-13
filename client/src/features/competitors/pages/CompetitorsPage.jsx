import { useState, useEffect } from "react";

const mockCompetitors = [
  { name: "Acme Corp", score: 92, marketShare: 28, trend: "+2%" },
  { name: "Globex Inc", score: 87, marketShare: 24, trend: "-1%" },
  { name: "Umbrella LLC", score: 80, marketShare: 18, trend: "+0.5%" },
  { name: "Initech", score: 75, marketShare: 15, trend: "+1%" },
  { name: "Hooli", score: 70, marketShare: 10, trend: "-0.5%" },
];

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
                <td className="py-2 px-4">{c.score}</td>
                <td className="py-2 px-4">{c.marketShare}</td>
                <td className="py-2 px-4">{c.trend}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-indigo-100 rounded p-4 text-indigo-900">
          <div className="text-lg font-bold">Top Competitor</div>
          <div className="text-xl">{topCompetitor ? topCompetitor.name : "-"}</div>
          <div className="text-sm text-indigo-700 mt-1">Score: {topCompetitor ? topCompetitor.score : "-"}</div>
        </div>
        <div className="bg-green-100 rounded p-4 text-green-900">
          <div className="text-lg font-bold">Average Score</div>
          <div className="text-xl">{avgScore}</div>
          <div className="text-sm text-green-700 mt-1">Across {competitors.length} competitors</div>
        </div>
      </div>
    </div>
  );
}
