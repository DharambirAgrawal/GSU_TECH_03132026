import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { DASHBOARD_NAV_ITEMS, ROUTES } from "../../app/paths";
import { authApi } from "../../services/authApi";
import {
  clearSessionToken,
  getSessionToken,
  setSessionToken,
} from "../../services/session";

export default function DashboardLayout() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function bootstrapSession() {
      const params = new URLSearchParams(window.location.search);
      const tokenFromUrl = params.get("session_token");

      if (tokenFromUrl) {
        setSessionToken(tokenFromUrl);
        window.history.replaceState({}, "", window.location.pathname);
      }

      const token = getSessionToken();
      if (!token) {
        navigate(ROUTES.login, { replace: true });
        return;
      }

      try {
        const data = await authApi.getMe(token);
        setProfile(data);
      } catch {
        clearSessionToken();
        navigate(`${ROUTES.login}?error=auth_error`, { replace: true });
      } finally {
        setIsLoading(false);
      }
    }

    bootstrapSession();
  }, [navigate]);

  const onLogout = async () => {
    const token = getSessionToken();
    if (!token) {
      navigate(ROUTES.login, { replace: true });
      return;
    }

    try {
      await authApi.logout(token);
    } catch {
      // Logout remains idempotent client-side.
    } finally {
      clearSessionToken();
      navigate(ROUTES.login, { replace: true });
    }
  };

  if (isLoading) {
    return (
      <main className="dashboard-shell">
        <section className="dashboard-card">
          <div className="spinner" aria-label="Loading" />
        </section>
      </main>
    );
  }

  return (
    <main className="workspace-shell">
      <aside className="workspace-sidebar">
        <p className="home-pill">Vigil Workspace</p>
        <h2>{profile?.company?.name || "Company"}</h2>
        <p className="sidebar-subtext">{profile?.user?.email}</p>

        <nav className="workspace-nav">
          {DASHBOARD_NAV_ITEMS.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                isActive ? "nav-link nav-link-active" : "nav-link"
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <button type="button" className="btn btn-secondary" onClick={onLogout}>
          Logout
        </button>
      </aside>

      <section className="workspace-content">
        <header className="workspace-header">
          <div>
            <h1>{profile?.company?.name || "Dashboard"}</h1>
            <p>
              Domain: {profile?.company?.approved_email_domain || "-"} · Role: {profile?.user?.role || "member"}
            </p>
          </div>
        </header>

        <Outlet context={{ profile }} />
      </section>
    </main>
  );
}
