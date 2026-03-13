import { Navigate, useLocation } from "react-router-dom";
import { ROUTES } from "../../app/paths";
import { getSessionToken, setSessionToken } from "../../services/session";

export default function ProtectedRoute({ children }) {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const tokenFromUrl = params.get("session_token");

  if (tokenFromUrl) {
    setSessionToken(tokenFromUrl);
    return children;
  }

  return getSessionToken() ? children : <Navigate to={ROUTES.login} replace />;
}
