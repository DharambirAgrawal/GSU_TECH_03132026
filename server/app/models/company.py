from app.extensions import db
from datetime import datetime, timezone
import enum


class IndustryType(enum.Enum):
    RETAIL = "retail"  # Home Depot, HEB, eBay
    FINANCIAL = "financial"  # Capital One
    TECHNOLOGY = "technology"  # Dell, Cisco
    MEDIA_SPORTS = "media_sports"  # NFL
    GROCERY = "grocery"  # HEB specifically


class Company(db.Model):
    __tablename__ = "companies"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(50), unique=True, nullable=False)
    # e.g. "capital_one", "home_depot", "dell"

    industry_type = db.Column(db.Enum(IndustryType), nullable=True)
    primary_domain = db.Column(db.String(255), nullable=False)
    # e.g. "https://www.homedepot.com"

    about_company = db.Column(db.Text)
    # Short profile entered at registration. Used to personalize query suggestions.

    approved_email_domain = db.Column(db.String(255))
    # Canonical company login domain used for magic-link auth.
    # Example: "amazon.com" allows anyone with *@amazon.com to sign in.

    registration_status = db.Column(db.String(30), default="approved")
    # For now auto-approved at registration as requested.
    # Future values: pending_review, approved, rejected, suspended.

    logo_url = db.Column(db.String(500))

    # Cached scores — recalculated after every query run batch
    # Stored here so dashboard reads are instant (no heavy query on load)
    ai_visibility_score = db.Column(db.Float, default=0.0)
    # 0-100: % of monitored queries where brand was mentioned this week

    accuracy_score = db.Column(db.Float, default=0.0)
    # 0-100: % of AI responses with all facts correct this week

    top_rec_rate = db.Column(db.Float, default=0.0)
    # 0-100: % of queries where brand is position #1 recommendation

    open_error_count = db.Column(db.Integer, default=0)
    # Count of active unresolved FactualErrors — shown as badge on dashboard

    bot_allowed = db.Column(db.Boolean, default=True)
    # False = GPTBot blocked in robots.txt — critical error flag

    last_crawled_at = db.Column(db.DateTime)
    last_queried_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users = db.relationship(
        "CompanyUser", back_populates="company", cascade="all, delete-orphan"
    )
    allowed_domains = db.relationship(
        "CompanyDomain", back_populates="company", cascade="all, delete-orphan"
    )
    simulations = db.relationship(
        "Simulation", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "industry_type": self.industry_type.value if self.industry_type else None,
            "primary_domain": self.primary_domain,
            "about_company": self.about_company,
            "approved_email_domain": self.approved_email_domain,
            "registration_status": self.registration_status,
            "logo_url": self.logo_url,
            "ai_visibility_score": self.ai_visibility_score,
            "accuracy_score": self.accuracy_score,
            "top_rec_rate": self.top_rec_rate,
            "open_error_count": self.open_error_count,
            "bot_allowed": self.bot_allowed,
            "last_crawled_at": (
                self.last_crawled_at.isoformat() if self.last_crawled_at else None
            ),
            "last_queried_at": (
                self.last_queried_at.isoformat() if self.last_queried_at else None
            ),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CompanyConfig(db.Model):
    """
    Optional per-company configuration overrides.
    Stores things like which LLM platforms to query,
    which pages to prioritize for crawling, and custom
    compliance rules for regulated industries.
    """

    __tablename__ = "company_configs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), unique=True, nullable=False
    )
    # unique=True: one config per company (one-to-one)

    enabled_platforms = db.Column(
        db.JSON, default=lambda: ["chatgpt", "gemini", "perplexity", "claude"]
    )
    # List of LLMPlatform values to query. Default: all 4 platforms.

    priority_pages = db.Column(db.JSON, default=list)
    # List of URLs to always crawl first. Override the default crawl order.

    compliance_mode = db.Column(db.Boolean, default=False)
    # True for financial companies — enables strict ethics flagging
    # and auto-alerts to legal when compliance_risk errors are found.

    alert_email = db.Column(db.String(255))
    # Where to send compliance alerts and operational notifications.

    default_query_count = db.Column(db.Integer, default=50)
    # Default number of prompts suggested in the frontend run modal.

    max_query_count = db.Column(db.Integer, default=100)
    # Safety cap for one manual run request to avoid accidental overload.

    auto_approve_domain_logins = db.Column(db.Boolean, default=True)
    # If True, any user with approved company domain can receive magic links.

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    company = db.relationship("Company", backref=db.backref("config", uselist=False))

    def __repr__(self):
        return f"<CompanyConfig company_id={self.company_id}>"
