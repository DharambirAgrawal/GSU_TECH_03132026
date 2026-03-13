import { useEffect, useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import AuthCard from "../../../components/common/AuthCard";
import { ROUTES } from "../../../app/paths";
import { authApi } from "../../../services/authApi";
import { getSessionToken, setSessionToken } from "../../../services/session";

export default function LoginPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [sessionToken, setSessionTokenInput] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const errorFromUrl = useMemo(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get("error");
    const map = {
      missing_token: "Token missing from verification link.",
      invalid_token: "Invalid token. Request a new magic link.",
      token_expired: "Magic link expired. Request a new one.",
      token_used: "Magic link already used. Request a new one.",
      auth_error: "Authentication failed. Please try again.",
    };

    return code ? map[code] || "Could not complete authentication." : "";
  }, [location.search]);

  useEffect(() => {
    if (getSessionToken()) {
      navigate(ROUTES.dashboard, { replace: true });
    }
  }, [navigate]);

  const onSubmitMagicLink = async (event) => {
    event.preventDefault();
    setMessage("");
    setError("");
    setIsSubmitting(true);

    try {
      const data = await authApi.requestMagicLink(email.trim());
      setMessage(data.message || "If your domain is registered, a magic link has been sent.");
      setEmail("");
    } catch (requestError) {
      setError(requestError.message || "Unable to request magic link.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const onSubmitToken = (event) => {
    event.preventDefault();
    if (!sessionToken.trim()) {
      setError("Paste a valid session token.");
      return;
    }

    setSessionToken(sessionToken.trim());
    navigate(ROUTES.dashboard, { replace: true });
  };

  return (
    <AuthCard
      title="Login with magic link"
      subtitle="Use your company email. We’ll send a one-time secure login link."
    >
      <form className="form" onSubmit={onSubmitMagicLink}>
        <label>
          Company email
          <input
            type="email"
            value={email}
            placeholder="dev.dharambir@amazon.com"
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>

        {errorFromUrl ? <div className="alert error">{errorFromUrl}</div> : null}
        {message ? <div className="alert success">{message}</div> : null}
        {error ? <div className="alert error">{error}</div> : null}

        <button className="btn btn-primary" type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Sending..." : "Send Magic Link"}
        </button>
      </form>

      <form className="form token-form" onSubmit={onSubmitToken}>
        <label>
          Already have session token?
          <input
            value={sessionToken}
            placeholder="Paste token and continue"
            onChange={(event) => setSessionTokenInput(event.target.value)}
          />
        </label>
        <button className="btn btn-secondary" type="submit">Go to Dashboard</button>
      </form>

      <p className="route-cta">
        Need to register first? <Link to={ROUTES.register}>Register company</Link>
      </p>
    </AuthCard>
  );
}
