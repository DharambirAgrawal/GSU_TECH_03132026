const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

export async function apiRequest(path, options = {}) {
  const { body, token, ...restOptions } = options;
  const headers = {
    "Content-Type": "application/json",
    ...(restOptions.headers || {}),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...restOptions,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : { message: await response.text() };

  if (!response.ok) {
    const error = new Error(payload.message || "Request failed.");
    error.status = response.status;
    throw error;
  }

  return payload;
}
