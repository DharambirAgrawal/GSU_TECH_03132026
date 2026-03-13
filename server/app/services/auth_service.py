"""
app/services/auth_service.py
----------------------------
Shared authentication helpers for domain-based magic-link login.

Responsibilities:
  - Token generation and SHA-256 hashing (never store raw tokens)
  - Domain normalisation from URL or email
  - Company + user creation at registration
  - Magic-link issuance (token → email via Power Automate)
  - Token verification and session creation
  - Bearer session guard for protected routes
  - Session revocation (logout)

All route handlers call into this service.
DB writes are kept here; routes stay thin.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import current_app

from app.extensions import db
from app.models.auth import CompanyDomain, CompanyUser, MagicLinkToken, UserSession
from app.models.company import Company, CompanyConfig
from app.services.emailing import send_email


# ---------------------------------------------------------------------------
# Utility — token hashing
# ---------------------------------------------------------------------------

def hash_token(raw_token: str) -> str:
    """
    Return the SHA-256 hex digest of a raw token string.
    Used for BOTH magic-link tokens and session tokens.

    We never store the raw value — only its hash.
    The raw value is sent to the user (email link / API response).
    The hash is what we look up in the database.

    Example:
        stored_hash = hash_token(raw)  # persisted in DB
        lookup_hash = hash_token(user_provided_raw)  # used for lookup
    """
    return hashlib.sha256(raw_token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Utility — domain normalisation
# ---------------------------------------------------------------------------

def normalize_domain(value: str) -> str:
    """
    Convert a URL or email address to a bare lowercase domain string.

    Examples:
        "https://www.amazon.com"  →  "amazon.com"
        "https://amazon.com/shop" →  "amazon.com"
        "User@Amazon.com"         →  "amazon.com"
        "ebay.com"                →  "ebay.com"
    """
    value = value.strip().lower()

    if "@" in value:
        # Email — take everything after the @
        return value.split("@", 1)[1]

    # URL — ensure it has a scheme so urlparse works correctly
    if not value.startswith(("http://", "https://")):
        value = "https://" + value

    parsed = urlparse(value)
    host = parsed.netloc or parsed.path   # netloc covers host:port
    host = host.split(":")[0]             # strip port if present

    if host.startswith("www."):
        host = host[4:]

    return host


# ---------------------------------------------------------------------------
# Company registration
# ---------------------------------------------------------------------------

def ensure_company_and_domain(
    company_name: str,
    company_url: str,
    about_company: str | None,
    contact_email: str,
) -> tuple:
    """
    Create a Company, its primary CompanyDomain, default CompanyConfig,
    and the registering user as 'owner'.

    Called ONCE at company registration — not at login.

    Args:
        company_name:  Display name of the company.
        company_url:   Company website URL (domain extracted from here).
        about_company: Optional free-text description used for prompt personalisation.
        contact_email: Email of the person registering. Becomes the owner account.

    Returns:
        (Company, CompanyDomain, CompanyUser)  — all already committed.

    Raises:
        ValueError: if the extracted domain is already registered.
    """
    domain = normalize_domain(company_url)

    # Guard: reject duplicate domain registrations
    existing = CompanyDomain.query.filter_by(domain=domain, is_active=True).first()
    if existing:
        raise ValueError(f"Domain '{domain}' is already registered.")

    # Build a URL-safe slug from the company name
    # Lowercase, spaces and dashes become underscores
    slug_base = (
        company_name.lower()
        .strip()
        .replace(" ", "_")
        .replace("-", "_")
    )
    slug = slug_base
    # Append a short random suffix on collision to guarantee uniqueness
    if Company.query.filter_by(slug=slug).first():
        slug = f"{slug_base}_{secrets.token_hex(3)}"

    company = Company(
        name=company_name,
        slug=slug,
        primary_domain=company_url,
        about_company=about_company,
        approved_email_domain=domain,
        registration_status="approved",
    )
    db.session.add(company)
    db.session.flush()  # Assign company.id before inserting related rows

    # Primary allowed login domain
    domain_record = CompanyDomain(
        company_id=company.id,
        domain=domain,
        is_primary=True,
        is_active=True,
    )
    db.session.add(domain_record)

    # Default company configuration (all fields default in the model)
    config_record = CompanyConfig(company_id=company.id)
    db.session.add(config_record)

    # First user — the person who registered — gets owner role
    owner = CompanyUser(
        company_id=company.id,
        email=contact_email.lower().strip(),
        role="owner",
    )
    db.session.add(owner)
    db.session.commit()

    return company, domain_record, owner


# ---------------------------------------------------------------------------
# Magic-link issuance
# ---------------------------------------------------------------------------

def issue_magic_link(user: CompanyUser, request_meta: dict) -> dict:
    """
    Generate a one-time magic-link token, persist its hash, and send the
    login email via Power Automate (emailing.send_email).

    Security notes:
      - A cryptographically secure random token is generated via
        secrets.token_urlsafe(32) \u2014 256 bits of entropy.
      - Only the SHA-256 hash of the token is stored in the DB.
      - The raw token is embedded in the email link and never logged.
      - Any existing unused tokens for this user remain valid until they
        expire \u2014 issuing a new link does not invalidate old ones.
        (Simplest UX: resend just works.)

    Args:
        user:         The CompanyUser requesting the link.
        request_meta: Dict containing optional keys: "ip", "user_agent".

    Returns:
        { "email": str, "expires_at": ISO-8601 str }

    Raises:
        Exception: propagated from send_email if email delivery fails.
    """
    raw = secrets.token_urlsafe(32)
    token_hash = hash_token(raw)

    ttl_minutes = int(current_app.config.get("MAGIC_LINK_TTL_MINUTES", 15))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

    token_record = MagicLinkToken(
        user_id=user.id,
        company_id=user.company_id,
        token_hash=token_hash,
        expires_at=expires_at,
        requested_from_ip=request_meta.get("ip"),
        requested_user_agent=request_meta.get("user_agent"),
    )
    db.session.add(token_record)
    db.session.commit()

    # Build the backend verify URL — backend handles verify then redirects to frontend.
    # This means the email link works even before the frontend is running.
    backend_url = current_app.config.get("BACKEND_BASE_URL", "http://localhost:5000")
    login_link = f"{backend_url}/api/auth/verify?token={raw}"

    send_email(
        recipient=user.email,
        subject="Your Vigil login link",
        message=(
            f"Hi,\n\n"
            f"Click the link below to log in to Vigil:\n\n"
            f"{login_link}\n\n"
            f"This link expires in {ttl_minutes} minutes and can only be used once.\n\n"
            f"If you didn't request this, you can safely ignore this email."
        ),
    )

    return {
        "email": user.email,
        "expires_at": expires_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Magic-link verification + session creation
# ---------------------------------------------------------------------------

def verify_magic_link_and_create_session(raw_token: str, request_meta: dict) -> dict:
    """
    Validate a raw magic-link token and issue a new authenticated session.

    Validation steps (all must pass):
      1. Token hash exists in magic_link_tokens table.
      2. Token has not expired (expires_at > now).
      3. Token has not already been used (used_at is None).

    On success:
      - Marks the token as used (used_at = now) — one-time enforcement.
      - Creates a UserSession with a new session token (hash-only in DB).
      - Updates user.last_login_at.

    Returns:
        {
            "session_token":      str,   # raw — store in frontend, send as Bearer
            "session_expires_at": str,   # ISO-8601 datetime
            "user": {
                "id", "email", "full_name", "role"
            },
            "company": {
                "id", "name", "approved_email_domain"
            }
        }

    Raises:
        ValueError: descriptive message for any validation failure.
                    Route handler maps this to HTTP 401.
    """
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    token_record = MagicLinkToken.query.filter_by(token_hash=token_hash).first()

    # --- Validation ---
    if token_record is None:
        raise ValueError("Invalid token.")

    # Make expires_at timezone-aware for comparison (DB may return naive datetime)
    expires_at = token_record.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise ValueError("Token has expired.")

    if token_record.used_at is not None:
        raise ValueError("Token has already been used.")

    # --- Consume the token (single-use) ---
    token_record.used_at = now

    # --- Create session ---
    raw_session = secrets.token_urlsafe(48)   # 384 bits of entropy
    session_hash = hash_token(raw_session)

    ttl_hours = int(current_app.config.get("SESSION_TTL_HOURS", 72))
    session_expires_at = now + timedelta(hours=ttl_hours)

    session_record = UserSession(
        user_id=token_record.user_id,
        company_id=token_record.company_id,
        session_token_hash=session_hash,
        expires_at=session_expires_at,
        created_from_ip=request_meta.get("ip"),
        created_user_agent=request_meta.get("user_agent"),
    )
    db.session.add(session_record)

    # Update last login timestamp
    user = CompanyUser.query.get(token_record.user_id)
    user.last_login_at = now

    db.session.commit()

    company = Company.query.get(token_record.company_id)

    return {
        # raw_session is returned exactly once — never stored as-is in the DB
        "session_token": raw_session,
        "session_expires_at": session_expires_at.isoformat(),
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
        },
        "company": {
            "id": company.id,
            "name": company.name,
            "approved_email_domain": company.approved_email_domain,
        },
    }


# ---------------------------------------------------------------------------
# Session guard — use at the top of every protected route
# ---------------------------------------------------------------------------

def require_company_session(request) -> tuple:
    """
    Extract and validate the Bearer session token from the incoming request.

    Reads:    Authorization: Bearer <session_token>
    Validates: token hash found, session not expired, session not revoked.

    Returns:
        (CompanyUser, Company) — both loaded from DB.
        All subsequent route logic is automatically company-scoped.

    Raises:
        PermissionError: descriptive message on any auth failure.
                         Route handlers convert this to HTTP 401.

    Usage inside a route handler:
        user, company = require_company_session(request)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise PermissionError("Missing or malformed Authorization header.")

    raw_token = auth_header.split(" ", 1)[1].strip()
    if not raw_token:
        raise PermissionError("Empty session token.")

    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)

    session = UserSession.query.filter_by(session_token_hash=token_hash).first()

    if session is None:
        raise PermissionError("Session not found.")

    if session.revoked_at is not None:
        raise PermissionError("Session has been revoked.")

    # Ensure timezone-aware comparison
    expires_at = session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < now:
        raise PermissionError("Session has expired.")

    user = CompanyUser.query.get(session.user_id)
    company = Company.query.get(session.company_id)

    return user, company


# ---------------------------------------------------------------------------
# Session revocation — logout
# ---------------------------------------------------------------------------

def revoke_session(raw_session_token: str) -> bool:
    """
    Mark a UserSession as revoked so it can no longer be used.

    Args:
        raw_session_token: The raw Bearer token the user wants to invalidate.

    Returns:
        True  — session found and revoked.
        False — token not found (already expired, or never existed).
                Treated as success to the caller (idempotent logout).
    """
    token_hash = hash_token(raw_session_token)
    session = UserSession.query.filter_by(session_token_hash=token_hash).first()

    if session is None:
        return False

    session.revoked_at = datetime.now(timezone.utc)
    db.session.commit()
    return True

#
# IMPORTS NEEDED:
#   import os
#   import secrets
#   import hashlib
#   from datetime import datetime, timezone, timedelta
#   from urllib.parse import urlparse
#   from app.extensions import db
#   from app.models.company import Company
#   from app.models.auth import CompanyDomain, CompanyUser, MagicLinkToken, UserSession
#
# -----------------------------------------------------------
# FUNCTION: normalize_domain(value: str) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Normalize URL/email input to plain lowercase domain.
#   Examples:
#     "https://www.amazon.com" -> "amazon.com"
#     "User@Amazon.com" -> "amazon.com"
#
# -----------------------------------------------------------
# FUNCTION: ensure_company_and_domain(...) -> Company
# -----------------------------------------------------------
# PURPOSE:
#   Create/update company and its primary allowed domain at registration.
#   For now, domain is auto-approved immediately.
#
# -----------------------------------------------------------
# FUNCTION: issue_magic_link(user: CompanyUser, request_meta: dict) -> dict
# -----------------------------------------------------------
# PURPOSE:
#   Generate one-time token, store token hash + expiry, and dispatch email.
#
# STEPS:
#   1. token = secrets.token_urlsafe(32)
#   2. token_hash = sha256(token)
#   3. Save MagicLinkToken(expires_at=now+15m)
#   4. Send email with frontend URL:
#        {FRONTEND_URL}/auth/verify?token=<raw_token>
#   5. Return metadata (never return token_hash).
#
# -----------------------------------------------------------
# FUNCTION: verify_magic_link_and_create_session(raw_token: str, request_meta: dict) -> dict
# -----------------------------------------------------------
# PURPOSE:
#   Validate token (exists, not expired, not used), mark it used,
#   and create a new UserSession.
#
# RETURNS:
#   {
#     "session_token": "...",
#     "session_expires_at": "...",
#     "user": CompanyUser,
#     "company": Company
#   }
#
# -----------------------------------------------------------
# FUNCTION: hash_token(raw_token: str) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Canonical hashing utility for both magic-link and session tokens.
#
# -----------------------------------------------------------
# FUNCTION: require_company_session(request) -> tuple[CompanyUser, Company]
# -----------------------------------------------------------
# PURPOSE:
#   Parse Bearer session token, validate against UserSession,
#   and return (user, company) context for route authorization.
#
# BEHAVIOR:
#   - Reject missing/invalid/expired/revoked sessions with 401 semantics.
#   - Ensures all routes are naturally company-scoped.
#
# -----------------------------------------------------------
# FUNCTION: revoke_session(raw_session_token: str) -> bool
# -----------------------------------------------------------
# PURPOSE:
#   Mark matching UserSession.revoked_at and return success flag.
