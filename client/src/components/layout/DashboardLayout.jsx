import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { DASHBOARD_NAV_ITEMS, ROUTES } from "../../app/paths";
import { authApi } from "../../services/authApi";
import { SIMULATION_DRAFT_KEY, simulationApi } from "../../services/simulationApi";
import {
  clearSessionToken,
  getSessionToken,
  setSessionToken,
} from "../../services/session";
import DashboardHeader from "./DashboardHeader";

export default function DashboardLayout() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasDraft, setHasDraft] = useState(false);

  const persistDraft = (draft) => {
    localStorage.setItem(SIMULATION_DRAFT_KEY, JSON.stringify(draft));
    setHasDraft(true);
  };

  const removeDraft = () => {
    localStorage.removeItem(SIMULATION_DRAFT_KEY);
    setHasDraft(false);
  };

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
        setHasDraft(Boolean(localStorage.getItem(SIMULATION_DRAFT_KEY)));
      } catch {
        clearSessionToken();
        navigate(`${ROUTES.login}?error=auth_error`, { replace: true });
      } finally {
        setIsLoading(false);
      }
    }

    bootstrapSession();
  }, [navigate]);

  const handleGenerateSimulation = async ({ product_specification, additional_detail, n_iteration }) => {
    const token = getSessionToken();
    if (!token) {
      navigate(ROUTES.login, { replace: true });
      return;
    }

    const response = await simulationApi.createQueries(
      { product_specification, additional_detail, n_iteration },
      token
    );

    const simulationId =
      response.simulation_id ||
      response.selection_id ||
      response.prompts?.[0]?.simulation_id ||
      null;

    const draft = {
      simulation_id: simulationId,
      product_specification,
      additional_detail: additional_detail || "",
      n_iteration,
      prompts: response.prompts || [],
      generated_at: new Date().toISOString(),
    };

    persistDraft(draft);
    navigate(ROUTES.queryTester, { state: { draft } });
  };

  const handleCancelDraft = async () => {
    const token = getSessionToken();
    const rawDraft = localStorage.getItem(SIMULATION_DRAFT_KEY);

    if (!token || !rawDraft) {
      removeDraft();
      return;
    }

    const draft = JSON.parse(rawDraft);
    if (draft?.simulation_id) {
      await simulationApi.cancelQueries(draft.simulation_id, token);
    }

    removeDraft();
  };

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
          <DashboardHeader
            profile={profile}
            onGenerate={handleGenerateSimulation}
            onCancelDraft={handleCancelDraft}
            hasDraft={hasDraft}
          />
        </header>

        <Outlet context={{ profile }} />
      </section>
    </main>
  );
}
