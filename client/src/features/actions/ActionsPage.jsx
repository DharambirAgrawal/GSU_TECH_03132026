import { AlertTriangle, ShieldAlert, Sparkles, Wrench } from "lucide-react";
import { useOutletContext } from "react-router-dom";

import {
  buildSeveritySummary,
  formatCompactNumber,
  getSeverityTone,
  safeArray,
  startCase,
  truncateText,
} from "../dashboard/analyticsUtils";

export default function ActionsPage() {
  const { analytics, analyticsError, isAnalyticsLoading } = useOutletContext();

  if (isAnalyticsLoading) {
    return <section className="page-card"><p>Loading actions analytics...</p></section>;
  }

  if (analyticsError) {
    return <section className="page-card"><h2>Actions unavailable</h2><p>{analyticsError}</p></section>;
  }

  if (!analytics || analytics.has_data === false) {
    return (
      <section className="page-card actions-page">
        <h2>Website Issues Detected</h2>
        <p>No action items yet. Run a simulation to discover issues and mitigations.</p>
      </section>
    );
  }

  const errorBreakdown = safeArray(analytics?.actions?.error_breakdown);
  const topFailureReasons = safeArray(analytics?.actions?.top_failure_reasons);
  const topMitigations = safeArray(analytics?.actions?.top_mitigations);
  const severitySummary = buildSeveritySummary(errorBreakdown);

  const actionPlan = [
    severitySummary.critical
      ? `Resolve ${severitySummary.critical} critical issues first to prevent trust and crawl damage.`
      : null,
    topFailureReasons[0]?.reason
      ? `Primary recurring failure: ${truncateText(topFailureReasons[0].reason, 120)}`
      : null,
    topMitigations[0]?.mitigation
      ? `Start with mitigation: ${truncateText(topMitigations[0].mitigation, 120)}`
      : null,
  ].filter(Boolean);

  return (
    <main className="dashboard-view page-shell">
      <section className="page-hero-card">
        <div>
          <div className="dashboard-eyebrow">Action center</div>
          <h2>Prioritized issues and mitigations</h2>
          <p>
            This view translates the backend actions payload into a triage board: issue counts, severity mix, recurring failures, and recommended mitigations.
          </p>
        </div>
      </section>

      <section className="metric-grid metric-grid-tight">
        <article className="metric-card tone-danger"><div className="metric-card-icon"><ShieldAlert size={18} /></div><div className="metric-card-copy"><p>Critical issues</p><h3>{formatCompactNumber(severitySummary.critical || 0)}</h3><span>must be resolved first</span></div></article>
        <article className="metric-card tone-warning"><div className="metric-card-icon"><AlertTriangle size={18} /></div><div className="metric-card-copy"><p>High severity</p><h3>{formatCompactNumber(severitySummary.high || 0)}</h3><span>direct impact on answer quality</span></div></article>
        <article className="metric-card tone-info"><div className="metric-card-icon"><Sparkles size={18} /></div><div className="metric-card-copy"><p>Failure reasons</p><h3>{formatCompactNumber(topFailureReasons.length)}</h3><span>recurring backend issue themes</span></div></article>
        <article className="metric-card tone-positive"><div className="metric-card-icon"><Wrench size={18} /></div><div className="metric-card-copy"><p>Mitigations</p><h3>{formatCompactNumber(topMitigations.length)}</h3><span>recommended fixes ready to execute</span></div></article>
      </section>

      <section className="dashboard-split-grid">
        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <h3>Issue breakdown</h3>
              <p>Backend payload: actions.error_breakdown</p>
            </div>
          </div>
          {errorBreakdown.length === 0 ? (
            <p className="panel-empty-copy">No errors detected in the current analytics window.</p>
          ) : (
            <div className="issue-grid">
              {errorBreakdown.map((item, index) => (
                <article key={`${item.type}-${item.severity}-${index}`} className={`issue-card tone-${getSeverityTone(item.severity)}`}>
                  <div className="issue-card-topline">
                    <strong>{startCase(item.type)}</strong>
                    <span className="severity-pill">{startCase(item.severity)}</span>
                  </div>
                  <h4>{formatCompactNumber(item.count)}</h4>
                  <p>Occurrences in the current analytics window.</p>
                </article>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-panel tone-info-surface">
          <div className="panel-heading">
            <div>
              <h3>Recommended sequence</h3>
              <p>Executive triage order</p>
            </div>
          </div>
          {actionPlan.length === 0 ? (
            <p className="panel-empty-copy">No urgent action sequence generated yet.</p>
          ) : (
            <ol className="ordered-action-list">
              {actionPlan.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ol>
          )}
        </article>
      </section>

      <section className="dashboard-split-grid">
        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <h3>Top failure reasons</h3>
              <p>Backend payload: actions.top_failure_reasons</p>
            </div>
          </div>
          <div className="card-stack">
            {topFailureReasons.length === 0 ? (
              <p className="panel-empty-copy">No recurring failure reasons yet.</p>
            ) : topFailureReasons.map((row, index) => (
              <article key={`${row.reason}-${index}`} className="detail-card">
                <div className="detail-card-count">{formatCompactNumber(row.count)}x</div>
                <p>{row.reason}</p>
              </article>
            ))}
          </div>
        </article>

        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <h3>Recommended mitigations</h3>
              <p>Backend payload: actions.top_mitigations</p>
            </div>
          </div>
          <div className="card-stack">
            {topMitigations.length === 0 ? (
              <p className="panel-empty-copy">No mitigation recommendations yet.</p>
            ) : topMitigations.map((row, index) => (
              <article key={`${row.mitigation}-${index}`} className="detail-card tone-positive">
                <div className="detail-card-count">{formatCompactNumber(row.count)}x</div>
                <p>{row.mitigation}</p>
              </article>
            ))}
          </div>
        </article>
      </section>
    </main>
  );
}
