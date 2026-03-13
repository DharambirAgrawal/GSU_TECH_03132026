from datetime import datetime, timezone

from app.extensions import db


class CompanyDomain(db.Model):
    """
    Allowed login domains for a company account.
    Primary use-case is company-wide access where any employee email
    matching this domain can authenticate and see the same dashboard.
    """

    __tablename__ = "company_domains"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    domain = db.Column(db.String(255), nullable=False)
    # Example: amazon.com, ebay.com

    is_primary = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="allowed_domains")


class CompanyUser(db.Model):
    """
    Lightweight user identity for company-domain access.
    No password is stored; authentication is magic-link only.
    """

    __tablename__ = "company_users"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    email = db.Column(db.String(320), nullable=False, index=True)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(50), default="member")
    # member/admin/owner

    is_active = db.Column(db.Boolean, default=True)
    last_login_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="users")
    magic_links = db.relationship(
        "MagicLinkToken", back_populates="user", cascade="all, delete-orphan"
    )
    sessions = db.relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    created_simulations = db.relationship("Simulation", back_populates="company_user")


class MagicLinkToken(db.Model):
    """
    One-time authentication token sent by email.
    User clicks link, token is verified, and a session is created.
    """

    __tablename__ = "magic_link_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("company_users.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    token_hash = db.Column(db.String(255), nullable=False)
    # Persist only token hash, never raw token.

    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)
    requested_from_ip = db.Column(db.String(100))
    requested_user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("CompanyUser", back_populates="magic_links")
    company = db.relationship("Company")


class UserSession(db.Model):
    """
    Session record created after successful magic-link verification.
    Supports stateless frontend by storing session token hash server-side.
    """

    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("company_users.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    session_token_hash = db.Column(db.String(255), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    revoked_at = db.Column(db.DateTime)

    created_from_ip = db.Column(db.String(100))
    created_user_agent = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("CompanyUser", back_populates="sessions")
    company = db.relationship("Company")
