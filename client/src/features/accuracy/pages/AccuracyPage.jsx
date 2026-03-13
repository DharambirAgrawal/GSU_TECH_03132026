import { AlertTriangle, Gauge, Link2Off, ShieldCheck, WandSparkles } from "lucide-react";
import { useOutletContext } from "react-router-dom";

import {
  formatCompactNumber,
  formatDate,
  formatScore,
  getTrendDelta,
  getTrendDirection,
  safeArray,
} from "../../dashboard/analyticsUtils";

function AccuracyChart({ data }) {
  const chartWidth = 640;
  const chartHeight = 220;
  const padding = 24;
  const maxValue = Math.max(...data.map((item) => item.value), 1);
  const minValue = Math.min(...data.map((item) => item.value), 0);
  const range = Math.max(maxValue - minValue, 1);

  const points = data.map((item, index) => {
    const x = padding + (index * (chartWidth - padding * 2)) / Math.max(data.length - 1, 1);
    const y = chartHeight - padding - ((item.value - minValue) / range) * (chartHeight - padding * 2);
    return `${x},${y}`;
  });

  return (
    <div className="trend-chart-card">
      <div className="panel-heading compact">
        <div>
          <h3>Accuracy trend</h3>
          <p>Backend payload: accuracy.trend</p>
        </div>
      </div>
      <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} className="trend-chart" aria-label="Accuracy trend">
        {data.map((item, index) => {
          const x = padding + (index * (chartWidth - padding * 2)) / Math.max(data.length - 1, 1);
          const y = chartHeight - padding - ((item.value - minValue) / range) * (chartHeight - padding * 2);

          return (
            <g key={item.date}>
              <circle cx={x} cy={y} r="5" className="trend-point" />
              <text x={x} y={chartHeight - 6} textAnchor="middle" className="trend-label">
                {item.shortDate}
              </text>
            </g>
          );
        })}
        <polyline points={points.join(" ")} className="trend-line" />
      </svg>
    </div>
  );
}

export default function AccuracyPage() {
  const { analytics, analyticsError, isAnalyticsLoading } = useOutletContext();
  const accuracy = analytics?.accuracy;

  if (isAnalyticsLoading) {
    return <section className="page-card"><p>Loading accuracy analytics...</p></section>;
  }

  if (analyticsError) {
    return <section className="page-card"><h2>Accuracy unavailable</h2><p>{analyticsError}</p></section>;
  }

  if (!analytics || analytics.has_data === false) {
    return (
      <section className="page-card">
        <h2>Accuracy Overview</h2>
        <p>No accuracy analytics yet. Run a simulation to populate this view.</p>
      </section>
    );
  }

  const scorePercent = Math.round(accuracy?.overall_score || 0);
  const history = safeArray(accuracy?.trend).map((row) => ({
    date: row.date,
    value: Math.round((row.avg_fact_score || 0) * 100),
    shortDate: formatDate(row.date),
  }));
  const trendDirection = getTrendDirection(accuracy?.trend);
  const trendDelta = getTrendDelta(accuracy?.trend);
  const totalRiskSignals =
    (accuracy?.low_confidence_checks || 0) +
    (accuracy?.hallucination_count || 0) +
    (accuracy?.dead_links_count || 0);

  return (
    <main className="dashboard-view page-shell">
      <section className="page-hero-card accuracy-hero-card">
        <div>
          <div className="dashboard-eyebrow">Accuracy analytics</div>
          <h2>How trustworthy your AI answers are</h2>
          <p>
            This page uses the backend accuracy payload: overall score, average fact score, dead links, hallucinations, low-confidence checks, and daily trend data.
          </p>
        </div>

        <div className="score-ring-wrap">
          <div className="score-ring" style={{ background: `conic-gradient(#6d28d9 ${scorePercent}%, rgba(109, 40, 217, 0.14) 0)` }}>
            <div className="score-ring-inner">
              <strong>{formatScore(scorePercent)}</strong>
              <span>overall accuracy</span>
            </div>
          </div>
        </div>
      </section>

      <section className="metric-grid metric-grid-tight">
        <article className="metric-card tone-positive">
          <div className="metric-card-icon"><ShieldCheck size={18} /></div>
          <div className="metric-card-copy">
            <p>Average fact score</p>
            <h3>{formatScore((accuracy?.avg_fact_score || 0) * 100)}</h3>
            <span>validated from backend fact checks</span>
          </div>
        </article>
        <article className="metric-card tone-warning">
          <div className="metric-card-icon"><Gauge size={18} /></div>
          <div className="metric-card-copy">
            <p>Low-confidence checks</p>
            <h3>{formatCompactNumber(accuracy?.low_confidence_checks || 0)}</h3>
            <span>likely to create weak product answers</span>
          </div>
        </article>
        <article className="metric-card tone-danger">
          <div className="metric-card-icon"><AlertTriangle size={18} /></div>
          <div className="metric-card-copy">
            <p>Hallucination flags</p>
            <h3>{formatCompactNumber(accuracy?.hallucination_count || 0)}</h3>
            <span>incorrect or unverifiable claims surfaced</span>
          </div>
        </article>
        <article className="metric-card tone-danger">
          <div className="metric-card-icon"><Link2Off size={18} /></div>
          <div className="metric-card-copy">
            <p>Dead links</p>
            <h3>{formatCompactNumber(accuracy?.dead_links_count || 0)}</h3>
            <span>citations that failed liveness checks</span>
          </div>
        </article>
      </section>

      <section className="dashboard-split-grid">
        <article className="dashboard-panel tone-info-surface">
          <div className="panel-heading">
            <div>
              <h3>Quality interpretation</h3>
              <p>Executive summary</p>
            </div>
          </div>
          <div className="summary-stack">
            <div className="summary-line"><span>Trend direction</span><strong>{trendDirection === "up" ? "Improving" : trendDirection === "down" ? "Declining" : "Stable"}</strong></div>
            <div className="summary-line"><span>Trend delta</span><strong>{trendDelta > 0 ? "+" : ""}{trendDelta.toFixed(1)} pts</strong></div>
            <div className="summary-line"><span>Total risk signals</span><strong>{formatCompactNumber(totalRiskSignals)}</strong></div>
          </div>
          <p className="panel-note">
            {scorePercent >= 80
              ? "Accuracy is strong. Focus on reducing the remaining low-confidence checks so models rely on cleaner evidence and fresher citations."
              : "Accuracy needs intervention. Prioritize hallucinations and dead links first because they directly reduce trust in AI-generated recommendations."}
          </p>
        </article>

        {history.length > 1 ? <AccuracyChart data={history} /> : <article className="dashboard-panel"><p className="panel-empty-copy">Trend data will appear after multiple days of fact checks.</p></article>}
      </section>

      <section className="dashboard-panel">
        <div className="panel-heading">
          <div>
            <h3>Recommended focus areas</h3>
            <p>Turn backend metrics into next steps</p>
          </div>
        </div>
        <div className="insight-grid insight-grid-compact">
          <article className="insight-card tone-warning">
            <div className="insight-card-head"><div className="metric-card-icon"><WandSparkles size={18} /></div><h3>Strengthen source content</h3></div>
            <p>Improve product pages and authoritative content where the fact score is weak so AI models can quote cleaner evidence.</p>
          </article>
          <article className="insight-card tone-danger">
            <div className="insight-card-head"><div className="metric-card-icon"><AlertTriangle size={18} /></div><h3>Remove hallucination triggers</h3></div>
            <p>Audit disputed claims, unsupported benefits, and stale data points that are causing the hallucination counter to rise.</p>
          </article>
          <article className="insight-card tone-danger">
            <div className="insight-card-head"><div className="metric-card-icon"><Link2Off size={18} /></div><h3>Repair citation paths</h3></div><p>Fix redirects, 404s, and outdated URLs so AI systems can keep finding live references for your brand.</p>
          </article>
        </div>
      </section>
    </main>
  );
}
