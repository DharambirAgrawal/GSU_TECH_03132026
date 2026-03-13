import { ArrowUpRight, Eye, Globe2, Link2, Sparkles } from "lucide-react";
import { useOutletContext } from "react-router-dom";

import {
  formatCompactNumber,
  formatDateTime,
  formatRelativeTime,
  formatScore,
  getMentionRate,
  getTopItem,
  getUniqueCount,
  safeArray,
  truncateText,
} from "../../dashboard/analyticsUtils";

export default function VisibilityPage() {
  const { analytics, analyticsError, isAnalyticsLoading } = useOutletContext();
  const visibility = analytics?.visibility;

  if (isAnalyticsLoading) {
    return <section className="page-card"><p>Loading visibility analytics...</p></section>;
  }

  if (analyticsError) {
    return <section className="page-card"><h2>Visibility unavailable</h2><p>{analyticsError}</p></section>;
  }

  if (!analytics || analytics.has_data === false) {
    return (
      <section className="page-card">
        <h2>Company Visibility</h2>
        <p>No visibility analytics yet. Run simulations to track mentions across models.</p>
      </section>
    );
  }

  const totalMentions = visibility?.total_mentions || 0;
  const platforms = safeArray(visibility?.mentions_by_model);
  const recentMentions = safeArray(visibility?.recent_mentions);
  const topModel = getTopItem(platforms);
  const mentionRate = getMentionRate(analytics);
  const uniqueDomains = getUniqueCount(recentMentions, (item) => item.domain);
  const maxMentions = Math.max(...platforms.map((item) => item.mentions || 0), 1);

  return (
    <main className="dashboard-view page-shell">
      <section className="page-hero-card">
        <div>
          <div className="dashboard-eyebrow">Visibility analytics</div>
          <h2>Where AI models are surfacing your brand</h2>
          <p>
            This view is powered by the backend visibility payload: total mentions, mentions by model, and recent citations with source URLs.
          </p>
        </div>
        <div className="hero-inline-note">
          <Sparkles size={16} />
          <span>{topModel ? `${topModel.model} is currently your top citation source.` : "Run more simulations to expand coverage."}</span>
        </div>
      </section>

      <section className="metric-grid metric-grid-tight">
        <article className="metric-card tone-info">
          <div className="metric-card-icon"><Eye size={18} /></div>
          <div className="metric-card-copy">
            <p>Total mentions</p>
            <h3>{formatCompactNumber(totalMentions)}</h3>
            <span>AI citations captured across all runs</span>
          </div>
        </article>
        <article className="metric-card tone-positive">
          <div className="metric-card-icon"><Link2 size={18} /></div>
          <div className="metric-card-copy">
            <p>Mention rate</p>
            <h3>{formatScore(mentionRate)}</h3>
            <span>Citations per backend model run</span>
          </div>
        </article>
        <article className="metric-card tone-neutral">
          <div className="metric-card-icon"><Globe2 size={18} /></div>
          <div className="metric-card-copy">
            <p>Source diversity</p>
            <h3>{formatCompactNumber(uniqueDomains)}</h3>
            <span>unique cited domains in recent mentions</span>
          </div>
        </article>
        <article className="metric-card tone-warning">
          <div className="metric-card-icon"><ArrowUpRight size={18} /></div>
          <div className="metric-card-copy">
            <p>Top model</p>
            <h3>{topModel?.model || "None"}</h3>
            <span>{topModel ? `${formatCompactNumber(topModel.mentions)} mentions` : "No model data yet"}</span>
          </div>
        </article>
      </section>

      <section className="dashboard-split-grid">
        <article className="dashboard-panel">
          <div className="panel-heading">
            <div>
              <h3>Mentions by platform</h3>
              <p>Backend payload: visibility.mentions_by_model</p>
            </div>
          </div>
          {platforms.length === 0 ? (
            <p className="panel-empty-copy">No platform mentions yet.</p>
          ) : (
            <div className="ranked-list">
              {platforms.map((platform) => (
                <div className="ranked-row" key={platform.model}>
                  <div>
                    <strong>{platform.model}</strong>
                    <span>{formatCompactNumber(platform.mentions)} mentions</span>
                  </div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${((platform.mentions || 0) / maxMentions) * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-panel tone-info-surface">
          <div className="panel-heading">
            <div>
              <h3>Visibility takeaway</h3>
              <p>Executive interpretation</p>
            </div>
          </div>
          <div className="summary-stack">
            <div className="summary-line"><span>Best-performing model</span><strong>{topModel?.model || "Not enough data"}</strong></div>
            <div className="summary-line"><span>Most recent refresh</span><strong>{formatRelativeTime(analytics?.generated_at)}</strong></div>
            <div className="summary-line"><span>Latest mention</span><strong>{recentMentions[0]?.domain || "No recent source"}</strong></div>
          </div>
          <p className="panel-note">
            {topModel
              ? `${topModel.model} is the clearest AI distribution channel for your brand today. Increase content quality on the domains it cites most often, then rerun simulations to confirm lift.`
              : "Once mentions start flowing in, this panel will explain which AI channel is delivering the best visibility and which domains are shaping the narrative."}
          </p>
        </article>
      </section>

      <section className="dashboard-panel">
        <div className="panel-heading">
          <div>
            <h3>Recent mentions</h3>
            <p>Backend payload: visibility.recent_mentions</p>
          </div>
        </div>
        {recentMentions.length === 0 ? (
          <p className="panel-empty-copy">No recent mentions available yet.</p>
        ) : (
          <div className="mention-grid">
            {recentMentions.map((mention, index) => (
              <article key={`${mention.model}-${mention.url || index}`} className="mention-card">
                <div className="mention-card-topline">
                  <strong>{mention.model}</strong>
                  <span>{formatDateTime(mention.timestamp)}</span>
                </div>
                <h4>{mention.domain || mention.company_cited || "Source unavailable"}</h4>
                <p>{truncateText(mention.prompt, 150) || "Prompt unavailable."}</p>
                <div className="mention-card-footer">
                  <span>{formatRelativeTime(mention.timestamp)}</span>
                  {mention.url ? (
                    <a href={mention.url} target="_blank" rel="noreferrer">
                      Open source
                    </a>
                  ) : null}
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
