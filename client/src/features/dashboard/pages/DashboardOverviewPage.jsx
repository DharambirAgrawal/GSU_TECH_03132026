import { useOutletContext, useNavigate } from "react-router-dom";
import { useState } from "react";
import "../../../styles/dashboard.css";

function StatCard({ title, value, sub, onClick, hoverDetails, color = "#6366f1" }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      className="stat-box"
      tabIndex={onClick ? 0 : undefined}
      role={onClick ? "button" : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e => (e.key === 'Enter' || e.key === ' ') && onClick()) : undefined}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ position: 'relative' }} // Ensure positioning context for absolute hoverDetails
    >
      <div style={{ fontSize: 13, color: color, fontWeight: 700, marginBottom: 2 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 800, color: color, marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 13, color: '#64748b', marginBottom: 2 }}>{sub}</div>
      {hovered && hoverDetails && (
        <div style={{
          position: 'absolute',
          left: '50%',
          top: '100%',
          transform: 'translateX(-50%)',
          marginTop: 8,
          background: '#fff',
          border: `1.5px solid ${color}`,
          borderRadius: 12,
          boxShadow: '0 4px 18px rgba(30,64,175,0.10)',
          padding: 14,
          minWidth: 220,
          zIndex: 10,
          fontSize: 13,
          color: '#334155',
          whiteSpace: 'normal',
        }}>
          {hoverDetails}
        </div>
      )}
    </div>
  );
}

export default function DashboardOverviewPage() {
  const { profile } = useOutletContext();
  const navigate = useNavigate();

  // Example data for hover details
  const accuracySpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Errors found: {profile?.company?.accuracy_errors ?? 2}</li>
      <li>Last audit: 2026-03-01</li>
      <li>Top competitors: <b>Acme Corp</b>, <b>Globex Inc</b></li>
    </ul>
  );
  const competitorsSpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Error Type: Acme Corp (92)</li>
      <li>Error Type: Globex Inc (87)</li>
    </ul>
  );
  const visibilitySpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Mentions: {profile?.company?.ai_visibility_score ?? 0}</li>
      <li>Recent: 5 new this week</li>
      <li>Sentiment: Positive</li>
    </ul>
  );

  const actionsSpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Blocked by robots.txt: {profile?.company?.robots_blocked ? "Yes" : "No"}</li>
      <li>Missing meta tags: {profile?.company?.missing_meta_tags ? "Yes" : "No"}</li>
    </ul>
  );

  return (
    <main>
      <section className="stats-grid dashboard-overview-grid">
        <StatCard
          title="Accuracy"
          value={profile?.company?.accuracy_score ?? 78}
          sub="Data accuracy score"
          color="#22c55e"
          onClick={() => navigate('/accuracy')}
          hoverDetails={accuracySpecs}
        />
        <StatCard
          title="Competitors"
          value="5 tracked"
          sub="Top 2 shown"
          color="#6366f1"
          onClick={() => navigate('/competitors')}
          hoverDetails={competitorsSpecs}
        />
        <StatCard
          title="Visibility"
          value={profile?.company?.ai_visibility_score ?? 0}
          sub="Mentions & sentiment"
          color="#f59e42"
          onClick={() => navigate('/visibility')}
          hoverDetails={visibilitySpecs}
        />

        <StatCard
          title="Action Items"
          value={profile?.company?.actions_count ?? 0}
          sub="Top 2 shown"
          color="#C41E3A"
          onClick={() => navigate('/actions')}
          hoverDetails={competitorsSpecs}
        />
      </section>
    </main>
  );
}
