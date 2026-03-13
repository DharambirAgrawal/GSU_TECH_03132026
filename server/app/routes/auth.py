"""
app/routes/auth.py
------------------
Blueprint for company registration and magic-link authentication.
URL prefix: /api/auth  (registered in app/__init__.py)

Auth model recap:
  - Company registers with its domain (e.g. amazon.com). Domain is auto-approved.
  - Any user at a matching domain email can request a magic link.
  - Link is sent via Power Automate. Email recipient is rewritten to @gmail.com (dev/test).
  - Verifying the link returns a 72-hour Bearer session token.
  - Every protected endpoint reads: Authorization: Bearer <session_token>

Endpoints:
  POST   /api/auth/register-company     Register new company workspace
  POST   /api/auth/request-magic-link   Send one-time login link by email
  POST   /api/auth/verify-magic-link    Exchange token for session
  GET    /api/auth/me                   Return current user + company (auth required)
  POST   /api/auth/logout               Revoke session (auth required)
"""

from __future__ import annotations

from flask import Blueprint, jsonify, redirect, request
from pydantic import BaseModel, EmailStr, ValidationError, field_validator

from app.extensions import db
from app.models.auth import CompanyDomain, CompanyUser
from app.services.auth_service import (
    ensure_company_and_domain,
    issue_magic_link,
    normalize_domain,
    require_company_session,
    revoke_session,
    verify_magic_link_and_create_session,
)

bp = Blueprint("auth", __name__)


# ---------------------------------------------------------------------------
# Request models (Pydantic v2)
# Pydantic validates the JSON body and provides clear error messages.
# ---------------------------------------------------------------------------

class RegisterCompanyRequest(BaseModel):
    company_name: str
    company_url: str
    contact_email: EmailStr
    about_company: str | None = None
    logo_url: str | None = None

    @field_validator("company_name")
    @classmethod
    def name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("company_name cannot be blank.")
        return v.strip()

    @field_validator("company_url")
    @classmethod
    def url_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("company_url cannot be blank.")
        return v.strip()


class RequestMagicLinkRequest(BaseModel):
    email: EmailStr


class VerifyMagicLinkRequest(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _request_meta() -> dict:
    """Capture request context for audit logging on tokens and sessions."""
    return {
        "ip": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", ""),
    }


def _parse_body(model_class):
    """
    Parse JSON body into the given Pydantic model.
    Returns (instance, None) on success or (None, error_response) on failure.
    Caller should check: body, err = _parse_body(MyModel); if err: return err
    """
    try:
        instance = model_class.model_validate(request.get_json(force=True) or {})
        return instance, None
    except ValidationError as e:
        return None, (jsonify({"success": False, "errors": e.errors()}), 400)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@bp.route("/register-company", methods=["POST"])
def register_company():
    """
    POST /api/auth/register-company

    Register a new company workspace on Vigil.

    - Extracts the login domain from company_url (e.g. "amazon.com").
    - Auto-approves the domain immediately (no manual review step for now).
    - Creates Company, CompanyDomain, CompanyConfig, and the owner CompanyUser.
    - The contact_email becomes the first user with role="owner".
    - Returns company info and owner user info.

    Request body:
        {
          "company_name": "Amazon",
          "company_url": "https://www.amazon.com",
          "contact_email": "admin@amazon.com",
          "about_company": "World's largest online marketplace"  (optional)
        }

    Responses:
        201  Created
        400  Validation error (missing/bad fields)
        409  Domain already registered
    """
    body, err = _parse_body(RegisterCompanyRequest)
    if err:
        return err

    try:
        company, domain_record, owner = ensure_company_and_domain(
            company_name=body.company_name,
            company_url=body.company_url,
            about_company=body.about_company,
            contact_email=str(body.contact_email),
        )
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 409

    return jsonify({
        "success": True,
        "message": (
            f"Company registered. Anyone with an @{company.approved_email_domain} "
            f"email can now log in."
        ),
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "approved_email_domain": company.approved_email_domain,
            "registration_status": company.registration_status,
        },
        "user": {
            "id": owner.id,
            "email": owner.email,
            "role": owner.role,
        },
    }), 201


@bp.route("/request-magic-link", methods=["POST"])
def request_magic_link():
    """
    POST /api/auth/request-magic-link

    Accept a company email address and send a one-time login link.

    Security: Always returns HTTP 200 with the same generic message,
    regardless of whether the domain is registered. This prevents
    account / domain enumeration attacks.

    Internal flow:
        1. Extract domain from submitted email.
        2. Look up active CompanyDomain.
        3. If found: upsert CompanyUser, call issue_magic_link().
        4. If not found: silently discard.

    Note on email delivery:
        The Power Automate flow rewrites the recipient to @gmail.com.
        E.g. admin@amazon.com → admin@gmail.com in actual delivery.
        This is intentional for dev/test environments.

    Request body:
        { "email": "user@amazon.com" }

    Response 200:
        { "success": true, "message": "If your domain is registered, a magic link has been sent." }
    """
    body, err = _parse_body(RequestMagicLinkRequest)
    if err:
        return err

    email = str(body.email).lower().strip()
    domain = normalize_domain(email)

    # Look up the domain — silently ignore if not found
    domain_record = CompanyDomain.query.filter_by(domain=domain, is_active=True).first()

    if domain_record:
        # Upsert: find existing user or create a new "member" account
        user = CompanyUser.query.filter_by(
            email=email,
            company_id=domain_record.company_id,
        ).first()

        if user is None:
            user = CompanyUser(
                company_id=domain_record.company_id,
                email=email,
                role="member",
            )
            db.session.add(user)
            db.session.commit()

        # Only dispatch if the user account is active
        if user.is_active:
            try:
                issue_magic_link(user, _request_meta())
            except Exception:
                # Don't expose email delivery failures to the caller.
                # In production: log this to your error tracker (Sentry, etc.)
                pass

    # Always return the same response — no enumeration leak
    return jsonify({
        "success": True,
        "message": "If your domain is registered, a magic link has been sent.",
    }), 200


@bp.route("/verify-magic-link", methods=["POST"])
def verify_magic_link():
    """
    POST /api/auth/verify-magic-link

    Exchange a raw magic-link token for an authenticated session.

    The frontend calls this when the user lands on /auth/verify?token=<raw>.
    It extracts the token from the URL query param and POSTs it here.

    On success, return a session_token that the frontend stores and sends
    as "Authorization: Bearer <session_token>" on every subsequent request.

    Request body:
        { "token": "<raw_token_from_email_link>" }

    Response 200:
        {
          "success": true,
          "session_token": "...",
          "session_expires_at": "2026-03-15T12:00:00Z",
          "user": { "id", "email", "full_name", "role" },
          "company": { "id", "name", "approved_email_domain" }
        }

    Response 401:
        Token invalid / expired / already used.
    """
    body, err = _parse_body(VerifyMagicLinkRequest)
    if err:
        return err

    try:
        result = verify_magic_link_and_create_session(body.token, _request_meta())
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 401

    return jsonify({"success": True, **result}), 200


@bp.route("/verify", methods=["GET"])
def verify_magic_link_redirect():
    """
    GET /api/auth/verify?token=<raw_token>

    This is the URL that gets sent in the magic-link email.
    The user clicks the link, lands here, and we:
      1. Verify the token
      2. Create a session
      3. Redirect to the frontend dashboard with session_token in the URL

    The frontend reads ?session_token= on load, stores it, and removes it
    from the URL (replaceState) to keep things clean.

    On success  → redirect to {FRONTEND_BASE_URL}/dashboard?session_token=...
    On failure  → redirect to {FRONTEND_BASE_URL}/login?error=<message>

    This pattern means the email link works even before the frontend is
    fully built — you can also just open the redirect URL manually to grab
    the session token for API testing.
    """
    from flask import current_app

    raw_token = request.args.get("token", "").strip()
    frontend_url = current_app.config.get("FRONTEND_BASE_URL", "http://localhost:3000")

    if not raw_token:
        return redirect(f"{frontend_url}/login?error=missing_token")

    try:
        result = verify_magic_link_and_create_session(raw_token, _request_meta())
    except ValueError as e:
        # Map the error to a short slug for the frontend to display a message
        error_map = {
            "Invalid token.": "invalid_token",
            "Token has expired.": "token_expired",
            "Token has already been used.": "token_used",
        }
        slug = error_map.get(str(e), "auth_error")
        return redirect(f"{frontend_url}/login?error={slug}")

    # Success — carry session token and basic user info to the frontend via URL.
    # Frontend must read these params on /dashboard load, store the token,
    # then strip the params from the URL using history.replaceState().
    session_token = result["session_token"]
    user_email = result["user"]["email"]
    company_name = result["company"]["name"]

    # In development: show an HTML debug page instead of redirecting to the
    # frontend (which may not be running yet). This lets you copy the session
    # token and test protected endpoints immediately.
    if current_app.config.get("DEBUG"):
        from flask import make_response
        dashboard_url = (
            f"{frontend_url}/dashboard"
            f"?session_token={session_token}"
            f"&email={user_email}"
            f"&company={company_name}"
        )
        html = f"""<!DOCTYPE html>
<html>
<head>
  <title>Vigil — Login Successful (Dev Mode)</title>
  <style>
    body {{ font-family: monospace; max-width: 700px; margin: 60px auto; padding: 0 20px; background: #0f0f0f; color: #e0e0e0; }}
    h2 {{ color: #4ade80; }}
    .token {{ background: #1a1a1a; border: 1px solid #333; padding: 16px; border-radius: 6px; word-break: break-all; font-size: 13px; }}
    .label {{ color: #888; font-size: 12px; margin-bottom: 6px; }}
    .note {{ color: #facc15; margin-top: 24px; font-size: 13px; line-height: 1.6; }}
    .copy-btn {{ background: #4ade80; color: #000; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-family: monospace; font-size: 13px; margin-top: 12px; }}
    hr {{ border-color: #333; margin: 24px 0; }}
    code {{ background: #1a1a1a; padding: 2px 6px; border-radius: 3px; }}
  </style>
</head>
<body>
  <h2>✓ Login successful</h2>
  <p>Authenticated as <strong>{user_email}</strong> &nbsp;·&nbsp; Company: <strong>{company_name}</strong></p>
  <hr>
  <div class="label">SESSION TOKEN (copy this for API testing)</div>
  <div class="token" id="token">{session_token}</div>
  <button class="copy-btn" onclick="navigator.clipboard.writeText(document.getElementById('token').innerText); this.innerText='Copied!'">Copy Token</button>
  <hr>
  <div class="label">Test a protected endpoint with this token:</div>
  <div class="token">curl http://localhost:5000/api/auth/me \\<br>&nbsp;&nbsp;-H "Authorization: Bearer {session_token}"</div>
  <div class="note">
    ⚠️ This page is shown in development mode only (DEBUG=True).<br>
    In production, this redirects to: <code>{dashboard_url}</code>
  </div>
</body>
</html>"""
        return make_response(html, 200)

    # Production: redirect to frontend dashboard
    return redirect(
        f"{frontend_url}/dashboard"
        f"?session_token={session_token}"
        f"&email={user_email}"
        f"&company={company_name}"
    )


@bp.route("/me", methods=["GET"])
def me():
    """
    GET /api/auth/me

    Return the current authenticated user's profile and their company context.

    This is typically called once on app mount by the frontend to:
      - Verify the stored session token is still valid.
      - Populate the user/company state in the frontend store.
      - Redirect to login if the session has expired.

    Headers required:
        Authorization: Bearer <session_token>

    Response 200:
        {
          "success": true,
          "user": { "id", "email", "full_name", "role", "last_login_at" },
          "company": { "id", "name", "slug", "approved_email_domain",
                       "ai_visibility_score", "accuracy_score" }
        }

    Response 401:
        Session missing / invalid / expired / revoked.
    """
    try:
        user, company = require_company_session(request)
    except PermissionError as e:
        return jsonify({"success": False, "message": str(e)}), 401

    return jsonify({
        "success": True,
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "slug": company.slug,
            "approved_email_domain": company.approved_email_domain,
            "ai_visibility_score": company.ai_visibility_score,
            "accuracy_score": company.accuracy_score,
        },
    }), 200


@bp.route("/logout", methods=["POST"])
def logout():
    """
    POST /api/auth/logout

    Revoke the current session so the Bearer token can no longer be used.
    The frontend should also clear its locally stored token.

    Accepts the session token from either:
      - JSON body:              { "session_token": "abc123..." }
      - Authorization header:   Authorization: Bearer abc123...

    Body takes precedence. Falls back to the Authorization header if no body.

    Response 200:
        { "success": true, "message": "Logged out." }

    Response 400:
        No session token provided in either location.
    """
    data = request.get_json(force=True, silent=True) or {}

    # Prefer body; fall back to Authorization header
    raw_token = data.get("session_token")
    if not raw_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            raw_token = auth_header.split(" ", 1)[1].strip()

    if not raw_token:
        return jsonify({"success": False, "message": "No session token provided."}), 400

    # Revoke — silently succeeds even if token is not found (idempotent)
    revoke_session(raw_token)

    return jsonify({"success": True, "message": "Logged out."}), 200

#
# AUTH MODEL:
#   - Company-level access by approved email domain.
#   - Any user with matching company domain can sign in.
#   - No passwords; login is email magic link only.
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from pydantic import BaseModel, EmailStr, ValidationError, Field
#   from app.extensions import db
#   from app.models.company import Company, CompanyConfig
#   from app.models.auth import CompanyDomain, CompanyUser
#   from app.services.auth_service import (
#       normalize_domain,
#       ensure_company_and_domain,
#       issue_magic_link,
#       verify_magic_link_and_create_session,
#       revoke_session,
#       hash_token,
#   )
#
# BLUEPRINT:
#   bp = Blueprint("auth", __name__)
#
# -----------------------------------------------------------
# REQUEST MODELS
# -----------------------------------------------------------
# class RegisterCompanyRequest(BaseModel):
#   company_name: str
#   company_url: str
#   about_company: str | None = None
#   contact_email: EmailStr
#   logo_url: str | None = None
#
# class RequestMagicLinkRequest(BaseModel):
#   email: EmailStr
#
# class VerifyMagicLinkRequest(BaseModel):
#   token: str
#
# class LogoutRequest(BaseModel):
#   session_token: str
#
# -----------------------------------------------------------
# ROUTE: POST /api/auth/register-company
# -----------------------------------------------------------
# PURPOSE:
#   Register a company workspace and approve its login domain.
#   For now, domain is auto-accepted immediately (no manual approval).
#
# LOGIC:
#   1. Validate body.
#   2. Normalize domain from company_url and contact_email.
#   3. Create Company with:
#        - name, primary_domain, about_company
#        - approved_email_domain = normalized domain
#        - registration_status = "approved"
#   4. Create CompanyDomain(is_primary=True, is_active=True).
#   5. Create CompanyConfig defaults (default_query_count/max_query_count).
#   6. Upsert first CompanyUser from contact_email (role="owner").
#   7. Return company summary + domain info.
#
# -----------------------------------------------------------
# ROUTE: POST /api/auth/request-magic-link
# -----------------------------------------------------------
# PURPOSE:
#   Accept email, match company by approved domain, and send magic link.
#
# LOGIC:
#   1. Validate email.
#   2. Extract domain from email.
#   3. Find active CompanyDomain(domain=...)
#   4. Upsert CompanyUser under matched company.
#   5. Call issue_magic_link(user, request_metadata) to create token + email.
#   6. Always return generic success to prevent account/domain enumeration.
#
# RESPONSE:
#   { "success": true, "message": "If your domain is allowed, a link has been sent." }
#
# -----------------------------------------------------------
# ROUTE: POST /api/auth/verify-magic-link
# -----------------------------------------------------------
# PURPOSE:
#   Verify one-time token and issue authenticated session token.
#
# LOGIC:
#   1. Validate token body.
#   2. verify_magic_link_and_create_session(token, request_metadata)
#   3. Return:
#       - session_token
#       - session_expires_at
#       - company summary
#       - user profile
#   4. Frontend stores session token and redirects to dashboard.
#
# -----------------------------------------------------------
# ROUTE: GET /api/auth/me
# -----------------------------------------------------------
# PURPOSE:
#   Resolve current user/session context and return company scope.
#
# INPUT:
#   Authorization: Bearer <session_token>
#
# RESPONSE:
#   {
#     "user": { "email": "user1@amazon.com", "role": "member" },
#     "company": { "id": 1, "name": "Amazon", "slug": "amazon" }
#   }
#
# -----------------------------------------------------------
# ROUTE: POST /api/auth/logout
# -----------------------------------------------------------
# PURPOSE:
#   Revoke current session token.
#
# LOGIC:
#   1. Hash provided session token.
#   2. Mark UserSession.revoked_at.
#   3. Return success.
