# app/services/auth_service.py
# -----------------------------------------
# Shared authentication helpers for domain-based magic-link login.
# Keeps token generation, hashing, verification, and session scoping
# out of route handlers.
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
