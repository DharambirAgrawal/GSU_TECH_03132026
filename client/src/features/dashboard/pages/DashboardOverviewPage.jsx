import {
  Activity,
  ArrowRight,
  Bot,
  Gauge,
  Radar,
  ShieldAlert,
  Sparkles,
  Workflow,
} from "lucide-react";
import { useNavigate, useOutletContext } from "react-router-dom";

import {
  buildSeveritySummary,
  formatCompactNumber,
  formatDateTime,
  formatRelativeTime,
  formatScore,
  getMentionRate,
  getPerformanceLabel,
  getTopItem,
  getTrendDirection,
  safeArray,
} from "../analyticsUtils";

function MetricCard({ icon: Icon, title, value, sub, tone = "positive", onClick }) {
  const handleKeyDown = (event) => {
    if (!onClick) {
      return;
    }

    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onClick();
    }
  };

  return (
    <article
      className={`metric-card tone-${tone}`}
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? "button" : undefined}
      onClick={onClick}
      onKeyDown={handleKeyDown}
    >
      <div className="metric-card-icon">
        <Icon size={18} />
      </div>
      <div className="metric-card-copy">
        <p>{title}</p>
        <h3>{value}</h3>
        <span>{sub}</span>
      </div>
      {onClick ? <ArrowRight size={16} className="metric-card-arrow" /> : null}
    </article>
  );
}

function InsightCard({ icon: Icon, title, description, tone = "neutral", actionLabel, onAction }) {
  return (
    <article className={`insight-card tone-${tone}`}>
      <div className="insight-card-head">
        <div className="metric-card-icon">
          <Icon size={18} />
        </div>
        <h3>{title}</h3>
      </div>
      <p>{description}</p>
      {onAction ? (
        <button type="button" className="insight-link" onClick={onAction}>
          {actionLabel}
          <ArrowRight size={14} />
        </button>
      ) : null}
    </article>
  );
}

export default function DashboardOverviewPage() {
  const { profile, analytics, analyticsError, isAnalyticsLoading } = useOutletContext();
  const navigate = useNavigate();
  const companyName = profile?.company?.name || "your company";
  const summary = analytics?.summary || {};
  const visibility = analytics?.visibility || {};
  const accuracy = analytics?.accuracy || {};
  const actions = analytics?.actions || {};
  const competitors = safeArray(analytics?.competitors?.top_domains);

  const cards = analytics?.cards || {
    accuracy_score: profile?.company?.accuracy_score ?? 0,
    visibility_score: profile?.company?.ai_visibility_score ?? 0,
    competitors_tracked: 0,
    action_items: 0,
  };

  const recentActivity = safeArray(analytics?.activity);
  const noData = analytics && analytics.has_data === false;
  const mentionRate = getMentionRate(analytics);
  const topModel = getTopItem(visibility?.mentions_by_model);
  const topCompetitor = competitors[0];
  const severitySummary = buildSeveritySummary(actions?.error_breakdown);
  const trendDirection = getTrendDirection(accuracy?.trend);

  const insights = [
    {
      icon: Radar,
      title: "Visibility pulse",
      description: topModel
        ? `${topModel.model} is driving the most citations right now with ${formatCompactNumber(topModel.mentions)} mentions. Mention rate is ${formatScore(mentionRate)} across all model runs.`
        : "Run simulations to learn which AI model is amplifying or ignoring your brand.",
      tone: cards.visibility_score >= 60 ? "positive" : "warning",
      actionLabel: "Open visibility view",
      onAction: () => navigate("/visibility"),
    },
    {
      icon: Gauge,
      title: "Accuracy risk",
      description:
        accuracy?.overall_score >= 75
          ? `Accuracy is holding at ${formatScore(accuracy.overall_score)}. Continue reducing ${accuracy?.low_confidence_checks || 0} low-confidence checks to protect trust.`
          : `Accuracy is at ${formatScore(accuracy.overall_score)} with ${accuracy?.hallucination_count || 0} hallucination flags and ${accuracy?.dead_links_count || 0} dead links to resolve.`,
      tone: accuracy?.overall_score >= 75 ? "positive" : "danger",
      actionLabel: "Review accuracy",
      onAction: () => navigate("/accuracy"),
    },
    {
      icon: Workflow,
      title: "Competitor pressure",
      description: topCompetitor
        ? `${topCompetitor.domain} leads external citations with ${formatCompactNumber(topCompetitor.mentions)} mentions. Protect your share before more discovery flows redirect buyers.`
        : "No competitor domains detected yet. This is a good baseline for your next simulation cycle.",
      tone: topCompetitor ? "info" : "neutral",
      actionLabel: "Inspect competitors",
      onAction: () => navigate("/competitors"),
    },
    {
      icon: ShieldAlert,
      title: "Priority actions",
      description: cards.action_items
        ? `${cards.action_items} high-priority items need attention, including ${severitySummary.critical || 0} critical and ${severitySummary.high || 0} high-severity issues.`
        : "No high-priority issues are open. Keep monitoring mitigations as new runs complete.",
      tone: cards.action_items ? "danger" : "positive",
      actionLabel: "Open action queue",
      onAction: () => navigate("/actions"),
    },
  ];

  return (
    <main className="dashboard-view">
      <section className="dashboard-hero">
        <div className="dashboard-hero-primary">
          <div className="dashboard-eyebrow">AI brand intelligence</div>
          <h2>{companyName} executive overview</h2>
          <p>
            Your frontend is now grounded in the backend analytics payload: simulations, model runs, citations, accuracy checks, competitor domains, and mitigation priorities.
          </p>

          <div className="hero-stat-grid">
            <div className="hero-stat">
              <span>Simulations</span>
              <strong>{formatCompactNumber(summary.total_simulations || 0)}</strong>
              <small>completed tracking cycles</small>
            </div>
            <div className="hero-stat">
              <span>Model runs</span>
              <strong>{formatCompactNumber(summary.total_model_runs || 0)}</strong>
              <small>responses analyzed</small>
            </div>
            <div className="hero-stat">
              <span>Citations</span>
              <strong>{formatCompactNumber(summary.total_citations || 0)}</strong>
              <small>brand/source mentions collected</small>
            </div>
          </div>
        </div>

        <aside className="dashboard-hero-secondary">
          <div className="hero-highlight">
            <div className="hero-highlight-icon">
              <Sparkles size={18} />
            </div>
            <div>
              <span className="hero-highlight-label">Current posture</span>
              <strong>{getPerformanceLabel(cards.accuracy_score)} visibility program</strong>
              <p>
                Accuracy trend is {trendDirection === "up" ? "improving" : trendDirection === "down" ? "slipping" : "stable"}. Last backend refresh: {formatRelativeTime(analytics?.generated_at)}.
              </p>
            </div>
          </div>

          <button className="btn btn-primary" onClick={() => navigate("/actions")}>View action queue</button>
        </aside>
      </section>

      {isAnalyticsLoading ? (
        <section className="dashboard-empty-state">
          <p>Loading analytics...</p>
        </section>
      ) : null}

      {!isAnalyticsLoading && analyticsError ? (
        <section className="dashboard-empty-state">
          <h2>Analytics unavailable</h2>
          <p>{analyticsError}</p>
        </section>
      ) : null}

      {!isAnalyticsLoading && !analyticsError && noData ? (
        <section className="dashboard-empty-state">
          <h2>No analytics yet</h2>
          <p>Create and run your first simulation to populate dashboard metrics.</p>
        </section>
      ) : null}

      {!isAnalyticsLoading && !analyticsError && !noData ? (
        <>
          <section className="metric-grid">
            <MetricCard
              icon={Gauge}
              title="Accuracy"
              value={formatScore(cards.accuracy_score)}
              sub={`${accuracy.low_confidence_checks || 0} low-confidence checks require follow-up`}
              tone={cards.accuracy_score >= 75 ? "positive" : "warning"}
              onClick={() => navigate("/accuracy")}
            />
            <MetricCard
              icon={Radar}
              title="Visibility"
              value={formatScore(cards.visibility_score)}
              sub={`${formatCompactNumber(visibility.total_mentions || 0)} mentions across ${safeArray(visibility.mentions_by_model).length} AI models`}
              tone={cards.visibility_score >= 60 ? "positive" : "warning"}
              onClick={() => navigate("/visibility")}
            />
            <MetricCard
              icon={Bot}
              title="Competitors"
              value={formatCompactNumber(cards.competitors_tracked || 0)}
              sub={topCompetitor ? `${topCompetitor.domain} is the leading cited competitor` : "No competitor pressure captured yet"}
              tone="info"
              onClick={() => navigate("/competitors")}
            />
            <MetricCard
              icon={ShieldAlert}
              title="Action items"
              value={formatCompactNumber(cards.action_items || 0)}
              sub={`${severitySummary.critical || 0} critical · ${severitySummary.high || 0} high severity`}
              tone={cards.action_items ? "danger" : "positive"}
              onClick={() => navigate("/actions")}
            />
          </section>

          <section className="insight-grid">
            {insights.map((insight) => (
              <InsightCard key={insight.title} {...insight} />
            ))}
          </section>

          <section className="dashboard-split-grid">
            <article className="dashboard-panel">
              <div className="panel-heading">
                <div>
                  <h3>Model coverage</h3>
                  <p>Backend payload: visibility.mentions_by_model</p>
                </div>
              </div>

              {safeArray(visibility.mentions_by_model).length === 0 ? (
                <p className="panel-empty-copy">No model coverage data yet.</p>
              ) : (
                <div className="ranked-list">
                  {safeArray(visibility.mentions_by_model).map((item) => {
                    const maxMentions = Math.max(...safeArray(visibility.mentions_by_model).map((row) => row.mentions || 0), 1);
                    const width = ((item.mentions || 0) / maxMentions) * 100;

                    return (
                      <div className="ranked-row" key={item.model}>
                        <div>
                          <strong>{item.model}</strong>
                          <span>{formatCompactNumber(item.mentions)} mentions</span>
                        </div>
                        <div className="bar-track">
                          <div className="bar-fill" style={{ width: `${width}%` }} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </article>

            <article className="dashboard-panel">
              <div className="panel-heading">
                <div>
                  <h3>Operational snapshot</h3>
                  <p>Backend payload: summary and actions</p>
                </div>
              </div>
              <div className="summary-stack">
                <div className="summary-line">
                  <span>Total prompts analyzed</span>
                  <strong>{formatCompactNumber(summary.total_prompts || 0)}</strong>
                </div>
                <div className="summary-line">
                  <span>Total errors found</span>
                  <strong>{formatCompactNumber(summary.total_errors || 0)}</strong>
                </div>
                <div className="summary-line">
                  <span>Average fact score</span>
                  <strong>{formatScore((summary.avg_fact_score || 0) * 100)}</strong>
                </div>
                <div className="summary-line">
                  <span>Last simulation status</span>
                  <strong>{summary.last_simulation_status || "Not started"}</strong>
                </div>
              </div>
            </article>
          </section>
        </>
      ) : null}

      {!isAnalyticsLoading && !analyticsError ? (
        <section className="dashboard-panel activity-panel">
          <div className="panel-heading">
            <div>
              <h3>Recent activity</h3>
              <p>Backend payload: activity</p>
            </div>
          </div>
          {recentActivity.length === 0 ? (
            <p className="panel-empty-copy">No recent activity yet.</p>
          ) : (
            <ul className="activity-feed">
              {recentActivity.map((item, idx) => (
                <li key={`${item.type}-${idx}`} className="activity-row">
                  <div className={`activity-badge tone-${item.type === "error" ? "danger" : item.type === "mention" ? "info" : "positive"}`}>
                    <Activity size={14} />
                  </div>
                  <div className="activity-copy">
                    <strong>{item.message || "Activity event"}</strong>
                    <span>{formatDateTime(item.timestamp)}</span>
                  </div>
                  <small>{formatRelativeTime(item.timestamp)}</small>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : null}
    </main>
  );
}
