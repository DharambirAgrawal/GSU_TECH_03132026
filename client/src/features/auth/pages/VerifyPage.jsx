import { useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import AuthCard from "../../../components/common/AuthCard";
import { ROUTES } from "../../../app/paths";
import { authApi } from "../../../services/authApi";
import { setSessionToken } from "../../../services/session";

export default function VerifyPage() {
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get("token");

    if (!token) {
      navigate(`${ROUTES.login}?error=missing_token`, { replace: true });
      return;
    }

    async function verifyMagicLink() {
      try {
        const data = await authApi.verifyMagicLink(token);
        setSessionToken(data.session_token);
        navigate(ROUTES.dashboard, { replace: true });
      } catch (requestError) {
        const text = String(requestError.message || "").toLowerCase();
        let slug = "auth_error";
        if (text.includes("invalid")) slug = "invalid_token";
        if (text.includes("expired")) slug = "token_expired";
        if (text.includes("used")) slug = "token_used";
        navigate(`${ROUTES.login}?error=${slug}`, { replace: true });
      }
    }

    verifyMagicLink();
  }, [location.search, navigate]);

  return (
    <AuthCard title="Checking your session" subtitle="Verifying your magic link and signing you in.">
      <div className="spinner" aria-label="Loading" />
    </AuthCard>
  );
}
