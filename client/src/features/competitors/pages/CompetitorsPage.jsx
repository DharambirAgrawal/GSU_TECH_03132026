import { Building2, Radar, Trophy, Users } from "lucide-react";
import { useOutletContext } from "react-router-dom";

import { formatCompactNumber, safeArray } from "../../dashboard/analyticsUtils";

export default function CompetitorsPage() {
  const { analytics, analyticsError, isAnalyticsLoading } = useOutletContext();
  const domains = safeArray(analytics?.competitors?.top_domains);
  const totalMentions = domains.reduce((sum, item) => sum + (item.mentions || 0), 0);

  const competitors = domains.map((item) => ({
    name: item.domain,
    score: item.mentions,
    marketShare: totalMentions ? Math.round((item.mentions / totalMentions) * 100) : 0,
  }));

  if (isAnalyticsLoading) {
    return <section className="page-card"><p>Loading competitors analytics...</p></section>;
  }

  if (analyticsError) {
    return <section className="page-card"><h2>Competitors unavailable</h2><p>{analyticsError}</p></section>;
  }

  if (!analytics || analytics.has_data === false || competitors.length === 0) {
    return (
      <section className="page-card">
        <h2>Top Competitors</h2>
        <p>No competitor domains detected yet. Run simulations to discover competitor citations.</p>
      </section>
    );
  }

  const topCompetitor = competitors[0];
  const avgScore = competitors.length ? competitors.reduce((sum, c) => sum + c.score, 0) / competitors.length : 0;
  const maxScore = Math.max(...competitors.map((item) => item.score || 0), 1);
  const concentration = competitors.slice(0, 3).reduce((sum, item) => sum + item.marketShare, 0);

  return (
    <main className="dashboard-view page-shell">
      <section className="page-hero-card">
        <div>
          <div className="dashboard-eyebrow">Competitor analytics</div>
          <h2>Which external domains are winning AI recommendation share</h2>
          <p>
            This page uses the backend competitor payload derived from cited domains. It shows which domains are most frequently referenced instead of your brand.
          </p>
        </div>
      </section>

      <section className="metric-grid metric-grid-tight">
        <article className="metric-card tone-info"><div className="metric-card-icon"><Building2 size={18} /></div><div className="metric-card-copy"><p>Tracked competitors</p><h3>{formatCompactNumber(competitors.length)}</h3><span>domains in the latest citation pool</span></div></article>
        <article className="metric-card tone-warning"><div className="metric-card-icon"><Trophy size={18} /></div><div className="metric-card-copy"><p>Top competitor</p><h3>{topCompetitor?.name || "None"}</h3><span>{topCompetitor ? `${formatCompactNumber(topCompetitor.score)} mentions` : "No competitor data yet"}</span></div></article>
        <article className="metric-card tone-neutral"><div className="metric-card-icon"><Users size={18} /></div><div className="metric-card-copy"><p>Average mentions</p><h3>{avgScore.toFixed(1)}</h3><span>across tracked domains</span></div></article>
        <article className="metric-card tone-danger"><div className="metric-card-icon"><Radar size={18} /></div><div className="metric-card-copy"><p>Top 3 share</p><h3>{concentration.toFixed(0)}%</h3><span>citation concentration among leaders</span></div></article>
      </section>

      <section className="dashboard-split-grid">
        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <h3>Competitor leaderboard</h3>
              <p>Backend payload: competitors.top_domains</p>
            </div>
          </div>
          <div className="ranked-list">
            {competitors.map((competitor, index) => (
              <div className="ranked-row ranked-row-detailed" key={competitor.name}>
                <div>
                  <strong>{index + 1}. {competitor.name}</strong>
                  <span>{formatCompactNumber(competitor.score)} mentions · {competitor.marketShare}% share</span>
                </div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${((competitor.score || 0) / maxScore) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
        </article>

        <article className="dashboard-panel tone-info-surface">
          <div className="panel-heading">
            <div>
              <h3>Competitive reading</h3>
              <p>Executive interpretation</p>
            </div>
          </div>
          <p className="panel-note">
            {topCompetitor
              ? `${topCompetitor.name} is the strongest external citation source right now, taking ${topCompetitor.marketShare}% of tracked competitor share. Strengthen your own authority pages for the prompts where this domain appears most often.`
              : "Once competitor domains appear in citations, this section will highlight the domains that are displacing your brand in AI answers."}
          </p>
          <div className="summary-stack">
            <div className="summary-line"><span>Total competitor mentions</span><strong>{formatCompactNumber(totalMentions)}</strong></div>
            <div className="summary-line"><span>Market concentration</span><strong>{concentration.toFixed(0)}%</strong></div>
            <div className="summary-line"><span>Leader gap</span><strong>{topCompetitor ? formatCompactNumber(topCompetitor.score - (competitors[1]?.score || 0)) : "0"}</strong></div>
          </div>
        </article>
      </section>
    </main>
  );
}
