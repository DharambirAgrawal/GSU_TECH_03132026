import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ROUTES } from "../../../app/paths";
import { getSessionToken } from "../../../services/session";
import { SIMULATION_DRAFT_KEY, simulationApi } from "../../../services/simulationApi";

export default function QueryTesterPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [draft, setDraft] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [showAllPrompts, setShowAllPrompts] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const stateDraft = location.state?.draft;
    const storedDraft = localStorage.getItem(SIMULATION_DRAFT_KEY);
    const initialDraft = stateDraft || (storedDraft ? JSON.parse(storedDraft) : null);

    if (!initialDraft) {
      setIsLoading(false);
      return;
    }

    async function bootstrapDraft() {
      const token = getSessionToken();
      if (!token) {
        navigate(ROUTES.login, { replace: true });
        return;
      }

      if (initialDraft.simulation_id && (!initialDraft.prompts || initialDraft.prompts.length === 0)) {
        try {
          const response = await simulationApi.getQueries(initialDraft.simulation_id, token);
          const hydratedDraft = { ...initialDraft, prompts: response.prompts || [] };
          localStorage.setItem(SIMULATION_DRAFT_KEY, JSON.stringify(hydratedDraft));
          setDraft(hydratedDraft);
        } catch (requestError) {
          setError(requestError.message || "Failed to load simulation prompts.");
          setDraft(initialDraft);
        } finally {
          setIsLoading(false);
        }
        return;
      }

      setDraft(initialDraft);
      setIsLoading(false);
    }

    bootstrapDraft();
  }, [location.state, navigate]);

  const handleCancel = async () => {
    setError("");
    setMessage("");
    setIsActionLoading(true);

    const token = getSessionToken();
    if (!token || !draft?.simulation_id) {
      localStorage.removeItem(SIMULATION_DRAFT_KEY);
      setDraft(null);
      navigate(ROUTES.dashboard);
      return;
    }

    try {
      await simulationApi.cancelQueries(draft.simulation_id, token);
      setMessage("Simulation draft cancelled.");
      localStorage.removeItem(SIMULATION_DRAFT_KEY);
      setDraft(null);
      setTimeout(() => navigate(ROUTES.dashboard), 250);
    } catch (requestError) {
      setError(requestError.message || "Failed to cancel draft.");
      setIsActionLoading(false);
    }
  };

  const handleStart = async () => {
    setError("");
    setMessage("");
    setIsActionLoading(true);

    const token = getSessionToken();
    if (!token || !draft?.simulation_id) {
      setError("Simulation id not available yet. Please generate again.");
      setIsActionLoading(false);
      return;
    }

    try {
      const response = await simulationApi.startSimulation(draft.simulation_id, token);
      setMessage(response.message || "Simulation started.");
      localStorage.removeItem(SIMULATION_DRAFT_KEY);
      setDraft(null);
      setTimeout(() => navigate(ROUTES.dashboard), 250);
    } catch (requestError) {
      setError(requestError.message || "Failed to start simulation.");
      setIsActionLoading(false);
    }
  };

  if (isLoading) {
    return <div className="page-card"><div className="spinner" aria-label="Loading" /></div>;
  }

  if (!draft) {
    return (
      <section className="page-card">
        <h2>Query Tester</h2>
        <p>No simulation draft found. Use "Create Simulation" from dashboard header.</p>
      </section>
    );
  }

  const prompts = draft.prompts || [];
  const previewLimit = 20;
  const visiblePrompts = showAllPrompts ? prompts : prompts.slice(0, previewLimit);
  const hasMorePrompts = prompts.length > previewLimit;

  return (
    <section className="page-card query-tester-card">
      <div className="query-tester-header">
        <div>
          <h2>Query Tester</h2>
          <p>
            Product: <b>{draft.product_specification}</b> · Iterations: <b>{draft.n_iteration}</b>
          </p>
          {draft.additional_detail ? <p>Additional detail: {draft.additional_detail}</p> : null}
        </div>
        <div className="query-summary-chip">{prompts.length} prompts</div>
      </div>

      {message ? <div className="alert success">{message}</div> : null}
      {error ? <div className="alert error">{error}</div> : null}

      <div className="query-list-scroller">
        <div className="query-list">
          {visiblePrompts.map((prompt, index) => (
            <article className="query-item" key={prompt.id || index}>
              <div className="query-index">#{(prompt.prompt_order ?? index) + 1}</div>
              <div className="query-text">{prompt.text}</div>
            </article>
          ))}
        </div>
      </div>

      {hasMorePrompts ? (
        <button
          type="button"
          className="btn btn-secondary"
          onClick={() => setShowAllPrompts((prev) => !prev)}
          disabled={isActionLoading}
        >
          {showAllPrompts ? "Show First 20" : "Show All " + prompts.length}
        </button>
      ) : null}

      <div className="modal-actions">
        <button type="button" className="btn btn-secondary" onClick={handleCancel} disabled={isActionLoading}>
          {isActionLoading ? "Processing..." : "Cancel"}
        </button>
        <button type="button" className="btn btn-primary" onClick={handleStart} disabled={isActionLoading}>
          {isActionLoading ? "Processing..." : "Start Simulation"}
        </button>
      </div>
    </section>
  );
}
