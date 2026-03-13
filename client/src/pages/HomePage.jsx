import { Link } from "react-router-dom";
import { ROUTES } from "../app/paths";

export default function HomePage() {
  return (
    <main className="home-shell">
      <section className="home-card">
        <p className="home-pill">AI Visibility Platform</p>
        <h1>Vigil</h1>
        <p>Start with authentication and dashboard. Feature modules are scaffolded for upcoming APIs.</p>
        <div className="home-actions">
          <Link className="btn btn-primary" to={ROUTES.register} color='#8219a2'>Register Company</Link>
          <Link className="btn btn-secondary" to={ROUTES.login}>Login</Link>
        </div>
      </section>
    </main>
  );
}
