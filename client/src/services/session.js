const SESSION_TOKEN_KEY = "vigil_session_token";

export function setSessionToken(token) {
  localStorage.setItem(SESSION_TOKEN_KEY, token);
}

export function getSessionToken() {
  return localStorage.getItem(SESSION_TOKEN_KEY);
}

export function clearSessionToken() {
  localStorage.removeItem(SESSION_TOKEN_KEY);
}
