import { useOutletContext, useNavigate } from "react-router-dom";
import { useState } from "react";

export default function DashboardOverviewPage() {
  const { profile } = useOutletContext();
  const [selectedProduct, setSelectedProduct] = useState("");
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customProduct, setCustomProduct] = useState("");
  const [showProductModal, setShowProductModal] = useState(true);
  const [productInput, setProductInput] = useState("");
  const [reasonInput, setReasonInput] = useState("");
  const productOptions = ["Product A", "Product B", "Product C"];
  const navigate = useNavigate();

  // Check localStorage for first-time user
  const [isFirstVisit, setIsFirstVisit] = useState(() => {
    return localStorage.getItem('hasVisitedDashboard') !== 'true';
  });

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
              style={{ display: 'block', width: '100%', marginBottom: 12 }}
            />
            <input
              type="text"
              placeholder="Why are you interested?"
              value={reasonInput}
              onChange={e => setReasonInput(e.target.value)}
              style={{ display: 'block', width: '100%', marginBottom: 12 }}
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
      <section className="stats-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 24 }}>
        {/* All stat cards same size */}
        <article
          className="stat stat-visibility stat-box"
          tabIndex={0}
          role="button"
          onClick={() => navigate("/visibility")}
          onKeyDown={e => (e.key === 'Enter' || e.key === ' ') && navigate("/visibility")}
          style={{ minHeight: 10, cursor: 'pointer', boxShadow: '0 4px 24px rgba(79,70,229,0.10)', background: '#f4f7fb', padding: 24 }}
        >
          <h2>Visibility</h2>
          <ul style={{ margin: '16px 0 0 0', padding: 0, listStyle: 'none', fontSize: 16 }}>
            <li>• Total mentions: <b>{profile?.company?.ai_visibility_score ?? 0}</b></li>
            <li>• Sentiment analysis</li>
            <li>• Platform breakdown</li>
            <li>• Recent mention examples</li>
          </ul>
        </article>
        <article className="stat stat-box" style={{ minHeight: 160, background: '#fff', padding: 24, cursor: 'default' }}>
          <h2>Company Domain</h2>
          <p>{profile?.company?.approved_email_domain || "-"}</p>
        </article>
        <article className="stat stat-box" style={{ minHeight: 160, background: '#fff', padding: 24, cursor: 'default' }}>
          <h2>Role</h2>
          <p>{profile?.user?.role || "member"}</p>
        </article>
        <article className="stat stat-box" style={{ minHeight: 160, background: '#fff', padding: 24, cursor: 'default' }}>
          <h2>Accuracy Score</h2>
          <p>{profile?.company?.accuracy_score ?? 0}</p>
        </article>
      </section>
    </main>
  );
}
