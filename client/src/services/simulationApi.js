import { apiRequest } from "./apiClient";

export const simulationApi = {
  createQueries: (body, token) =>
    apiRequest("/api/agent/queries", {
      method: "POST",
      token,
      body,
    }),

  getQueries: (simulationId, token) =>
    apiRequest(`/api/agent/queries/${simulationId}`, {
      method: "GET",
      token,
    }),

  cancelQueries: (simulationId, token) =>
    apiRequest("/api/agent/queries/cancel", {
      method: "POST",
      token,
      body: { simulation_id: simulationId },
    }),

  startSimulation: (selectionId, token) =>
    apiRequest("/api/agents/simulations", {
      method: "POST",
      token,
      body: { selection_id: selectionId },
    }),

  generatePdfReport: ({ simulation_id, company_department }, token) =>
    apiRequest("/api/agents/pdfs", {
      method: "POST",
      token,
      body: { simulation_id, company_department },
    }),
};

export const SIMULATION_DRAFT_KEY = "vigil_simulation_draft";
