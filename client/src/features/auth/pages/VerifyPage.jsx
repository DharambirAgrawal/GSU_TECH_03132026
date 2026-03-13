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

    verifyMagicLink();
  }, [location.search, navigate]);

  return (
    <AuthCard title="Checking your session" subtitle="Verifying your magic link and signing you in.">
      <div className="spinner" aria-label="Loading" />
    </AuthCard>
  );
}
