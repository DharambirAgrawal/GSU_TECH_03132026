import { apiRequest } from "./apiClient";

export const metricsApi = {
  /**
   * Get dashboard overview stats: accuracy, visibility, competitors, actions
   */
  getDashboardStats: (token) =>
    apiRequest("/api/metrics/dashboard", {
      method: "GET",
      token,
    }),

  /**
   * Get detailed accuracy/fact-check data
   */
  getAccuracyDetails: (token) =>
    apiRequest("/api/metrics/accuracy", {
      method: "GET",
      token,
    }),

  /**
   * Get visibility data: mentions by platform, sentiment
   */
  getVisibilityDetails: (token) =>
    apiRequest("/api/metrics/visibility", {
      method: "GET",
      token,
    }),

  /**
   * Get competitor analysis data
   */
  getCompetitorsDetails: (token) =>
    apiRequest("/api/metrics/competitors", {
      method: "GET",
      token,
    }),

  /**
   * Get actions/errors data
   */
  getActionsDetails: (token) =>
    apiRequest("/api/metrics/actions", {
      method: "GET",
      token,
    }),
};
