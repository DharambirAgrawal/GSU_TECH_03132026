import { useOutletContext, useNavigate } from "react-router-dom";

export default function DashboardOverviewPage() {
  const { profile } = useOutletContext();
  const navigate = useNavigate();

  return (
    <main>
      <section className="stats-grid dashboard-overview-grid">
        
        <article
          className="stat stat-visibility stat-box"
          tabIndex={0}
          role="button"
          onClick={() => navigate("/visibility")}
          onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && navigate("/visibility")}
          style={{ cursor: "pointer" }}
        >
          <h2>Visibility</h2>
          <ul className="overview-list">
            <li>• Total mentions: <b>{profile?.company?.ai_visibility_score ?? 0}</b></li>
            <li>• Sentiment analysis</li>
            <li>• Platform breakdown</li>
            <li>• Recent mention examples</li>
          </ul>
        </article>
        <article className="stat stat-box">
          <h2>Company Domain</h2>
          <p>{profile?.company?.approved_email_domain || "-"}</p>
        </article>
        <article className="stat stat-box">
          <h2>Role</h2>
          <p>{profile?.user?.role || "member"}</p>
        </article>
        <article className="stat stat-box">
          <h2>Accuracy Score</h2>
          <p>{profile?.company?.accuracy_score ?? 0}</p>
        </article>
      </section>
    </main>
  );
}
