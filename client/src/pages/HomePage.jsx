import { Link, useNavigate } from "react-router-dom";
import { ROUTES } from "../app/paths";
import vigilLogo from "../assets/vigil_logopurple_128px.png";

export default function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="home-page-split">

      <div className="home-welcome-panel">
        <div className="welcome-content">
          <img src={vigilLogo} alt="Vigil Logo" className="welcome-logo" />
          <h1>Welcome to Vigil</h1>
          <p className="welcome-subtitle">
            Your AI brand intelligence platform for monitoring and optimizing how AI systems represent your brand.
          </p>

          <ul className="welcome-features">
            <li>
              <span className="feature-icon">🔍</span>
              <div>
                <strong>AI Visibility Tracking</strong>
                <p>Monitor how often AI models mention and recommend your brand</p>
              </div>
            </li>
            <li>
              <span className="feature-icon">✓</span>
              <div>
                <strong>Accuracy Monitoring</strong>
                <p>Detect hallucinations and misinformation about your products</p>
              </div>
            </li>
            <li>
              <span className="feature-icon">📊</span>
              <div>
                <strong>Competitor Analysis</strong>
                <p>See how your brand stacks up against competitors in AI responses</p>
              </div>
            </li>
            <li>
              <span className="feature-icon">⚡</span>
              <div>
                <strong>Actionable Insights</strong>
                <p>Get recommendations to improve your AI presence</p>
              </div>
            </li>
          </ul>
        </div>
      </div>

      <div className="home-cta-panel">
        <div className="home-cta-container">
          <div className="ready-prompt">
            <h2>Ready to get started?</h2>
            <p>Sign in to your account or register your company to begin.</p>
          </div>

          <div className="home-cta-buttons">
            <button 
              type="button" 
              className="btn btn-primary btn-large"
              onClick={() => navigate(ROUTES.login)}
            >
              Sign In
            </button>
            <button 
              type="button" 
              className="btn btn-secondary btn-large"
              onClick={() => navigate(ROUTES.register)}
            >
              Register Company
            </button>
          </div>

          <p className="home-cta-note">
            New to Vigil? Register your company first to get started.
          </p>
        </div>
      </div>
    </div>
  );
}
