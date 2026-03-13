import { apiRequest } from "./apiClient";

export const dashboardApi = {
  getAnalytics: (token) =>
    apiRequest("/api/dashboard/analytics", {
      method: "GET",
      token,
    }),
};
