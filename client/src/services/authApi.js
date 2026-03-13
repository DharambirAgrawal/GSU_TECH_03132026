import { apiRequest } from "./apiClient";

export const authApi = {
  registerCompany: (body) =>
    apiRequest("/api/auth/register-company", { method: "POST", body }),

  requestMagicLink: (email) =>
    apiRequest("/api/auth/request-magic-link", {
      method: "POST",
      body: { email },
    }),

  verifyMagicLink: (token) =>
    apiRequest("/api/auth/verify-magic-link", {
      method: "POST",
      body: { token },
    }),

  getMe: (token) => apiRequest("/api/auth/me", { method: "GET", token }),

  logout: (token) =>
    apiRequest("/api/auth/logout", {
      method: "POST",
      token,
      body: { session_token: token },
    }),
};
