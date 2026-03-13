import { useOutletContext, useNavigate } from "react-router-dom";
<<<<<<< HEAD
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
      style={{
        cursor: onClick ? "pointer" : "default",
        background: hovered ? "#f1f5f9" : "#fff",
        boxShadow: hovered ? `0 8px 32px ${color}22` : "0 4px 24px rgba(79,70,229,0.10)",
        border: `2px solid ${hovered ? color : '#e0e7ef'}`,
        borderRadius: 16,
        padding: 24,
        minHeight: 120,
        transition: 'all 0.18s',
        position: 'relative',
        outline: 'none',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'center',
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div style={{ fontSize: 13, color: color, fontWeight: 700, marginBottom: 2 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 800, color: color, marginBottom: 2 }}>{value}</div>
      <div style={{ fontSize: 13, color: '#64748b', marginBottom: 2 }}>{sub}</div>
      {hovered && hoverDetails && (
        <div style={{
          position: 'absolute',
          left: 0,
          top: '100%',
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
        }}>
          {hoverDetails}
        </div>
      )}
    </div>
  );
}
=======
>>>>>>> 9d0f09da1b49760ef77d5065bd6dbc5985f66150

export default function DashboardOverviewPage() {
  const { profile } = useOutletContext();
  const navigate = useNavigate();

<<<<<<< HEAD
  // Check localStorage for first-time user
  const [isFirstVisit, setIsFirstVisit] = useState(() => {
    return localStorage.getItem('hasVisitedDashboard') !== 'true';
  });

  //hover details example
  const accuracySpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Errors found: {profile?.company?.accuracy_errors ?? 2}</li>
      <li>Last audit: 2026-03-01</li>
      <li>Top competitors: <b>Acme Corp</b>, <b>Globex Inc</b></li>
    </ul>
  );
  const competitorsSpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Top 1: Acme Corp (92)</li>
      <li>Top 2: Globex Inc (87)</li>
    </ul>
  );
  const visibilitySpecs = (
    <ul style={{ margin: 0, paddingLeft: 18 }}>
      <li>Mentions: {profile?.company?.ai_visibility_score ?? 0}</li>
      <li>Recent: 5 new this week</li>
      <li>Sentiment: Positive</li>
    </ul>
  );

  return (
    <main>
      {/* Product selection modal for first-time users */}
      {showProductModal && !selectedProduct && isFirstVisit && (
        <div className="modal-backdrop">
          <div className="modal">
            <h2>Welcome!</h2>
            <p>What product would you like to see data on?</p>
            <input
              type="text"
              placeholder="Enter product name"
              value={productInput}
              onChange={e => setProductInput(e.target.value)}
            />
            <input
              type="text"
              placeholder="Why are you interested?"
              value={reasonInput}
              onChange={e => setReasonInput(e.target.value)}
              
            />
            <button
              onClick={() => {
                setShowProductModal(false);
                setSelectedProduct(productInput);
                localStorage.setItem('hasVisitedDashboard', 'true');
                navigate("/query-tester", { state: { product: productInput, reason: reasonInput } });
              }}
              disabled={!productInput || !reasonInput}
              style={{ width: '100%', padding: 8 }}
            >
              Submit
            </button>
          </div>
        </div>
      )}
      <section className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
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
=======
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
>>>>>>> 9d0f09da1b49760ef77d5065bd6dbc5985f66150
      </section>
    </main>
  );
}
