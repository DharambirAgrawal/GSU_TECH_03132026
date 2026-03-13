import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { DASHBOARD_NAV_ITEMS, ROUTES } from "../../app/paths";
import { authApi } from "../../services/authApi";
import { dashboardApi } from "../../services/dashboardApi";
import { SIMULATION_DRAFT_KEY, simulationApi } from "../../services/simulationApi";
import {
  clearSessionToken,
  getSessionToken,
  setSessionToken,
} from "../../services/session";
import DashboardHeader from "./DashboardHeader";
import vigilLogo from "../../assets/vigil_logopurple.png";
import "../../styles/dashboard.css";

export default function DashboardLayout() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [analyticsError, setAnalyticsError] = useState("");
  const [isAnalyticsLoading, setIsAnalyticsLoading] = useState(true);
  const [isLoading, setIsLoading] = useState(true);
  const [hasDraft, setHasDraft] = useState(false);
  const [draft, setDraft] = useState(null);

  const setSimulationIdInUrl = (simulationId) => {
    const url = new URL(window.location.href);
    if (simulationId) {
      url.searchParams.set("simulation_id", simulationId);
    } else {
      url.searchParams.delete("simulation_id");
    }
    window.history.replaceState({}, "", `${url.pathname}${url.search}`);
  };

  const persistDraft = (draft) => {
    localStorage.setItem(SIMULATION_DRAFT_KEY, JSON.stringify(draft));
    setDraft(draft);
    setHasDraft(true);
    setSimulationIdInUrl(draft?.simulation_id);
  };

  const removeDraft = () => {
    localStorage.removeItem(SIMULATION_DRAFT_KEY);
    setDraft(null);
    setHasDraft(false);
    setSimulationIdInUrl(null);
  };

  const hydrateDraft = async (token) => {
    const params = new URLSearchParams(window.location.search);
    const simulationIdFromUrl = params.get("simulation_id");

    let localDraft = null;
    try {
      localDraft = JSON.parse(localStorage.getItem(SIMULATION_DRAFT_KEY) || "null");
    } catch {
      localDraft = null;
    }

    const simulationId = simulationIdFromUrl || localDraft?.simulation_id;
    if (!simulationId) {
      setDraft(null);
      setHasDraft(false);
      return;
    }

    try {
      const response = await simulationApi.getQueries(simulationId, token);
      const mergedDraft = {
        simulation_id: simulationId,
        product_specification: localDraft?.product_specification || "",
        additional_detail: localDraft?.additional_detail || "",
        n_iteration: localDraft?.n_iteration || response.prompts?.length || 0,
        prompts: response.prompts || [],
        generated_at: localDraft?.generated_at || new Date().toISOString(),
      };
      persistDraft(mergedDraft);
    } catch {
      removeDraft();
    }
  };

  const fetchAnalytics = async (token) => {
    try {
      setIsAnalyticsLoading(true);
      setAnalyticsError("");
      const analyticsPayload = await dashboardApi.getAnalytics(token);
      setAnalytics(analyticsPayload);
    } catch (analyticsRequestError) {
      setAnalytics(null);
      setAnalyticsError(analyticsRequestError.message || "Failed to load analytics.");
    } finally {
      setIsAnalyticsLoading(false);
    }
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
        await hydrateDraft(token);
        await fetchAnalytics(token);
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

    if (!simulationId) {
      throw new Error("Simulation ID missing from server response.");
    }

    const draft = {
      simulation_id: simulationId,
      product_specification,
      additional_detail: additional_detail || "",
      n_iteration,
      prompts: response.prompts || [],
      generated_at: new Date().toISOString(),
    };

    persistDraft(draft);
    return {
      simulation_id: simulationId,
      prompts_count: draft.prompts.length,
    };
  };

  const handleStartDraft = async () => {
    const token = getSessionToken();
    if (!token) {
      navigate(ROUTES.login, { replace: true });
      return;
    }

    const simulationId = draft?.simulation_id;
    if (!simulationId) {
      throw new Error("No draft simulation found.");
    }

    const startResult = await simulationApi.startSimulation(simulationId, token);
    removeDraft();
    await fetchAnalytics(token);

    return {
      simulation_id: simulationId,
      mode: startResult?.mode,
      task_id: startResult?.task_id,
    };
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
        <div className="sidebar-logo">
          <img src={vigilLogo} alt="Vigil Logo" className="sidebar-logo-img" />
        </div>
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
            analytics={analytics}
            onGenerate={handleGenerateSimulation}
            onStartDraft={handleStartDraft}
            onCancelDraft={handleCancelDraft}
            hasDraft={hasDraft}
            draft={draft}
          />
        </header>

        <Outlet
          context={{
            profile,
            analytics,
            analyticsError,
            isAnalyticsLoading,
          }}
        />
      </section>
    </main>
  );
}
