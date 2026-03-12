# app/routes/auth.py
# -----------------------------------------
# Blueprint for company registration and magic-link authentication.
# Registered in create_app() at URL prefix: /api/auth
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
