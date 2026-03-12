from app.extensions import db
from datetime import datetime, timezone
import enum


class IndustryType(enum.Enum):
    RETAIL       = "retail"        # Home Depot, HEB, eBay
    FINANCIAL    = "financial"     # Capital One
    TECHNOLOGY   = "technology"    # Dell, Cisco
    MEDIA_SPORTS = "media_sports"  # NFL
    GROCERY      = "grocery"       # HEB specifically


class Company(db.Model):
    __tablename__ = "companies"

    id                  = db.Column(db.Integer, primary_key=True)
    name                = db.Column(db.String(100), nullable=False)
    slug                = db.Column(db.String(50), unique=True, nullable=False)
    # e.g. "capital_one", "home_depot", "dell"

    industry_type       = db.Column(db.Enum(IndustryType), nullable=False)
    primary_domain      = db.Column(db.String(255), nullable=False)
    # e.g. "https://www.homedepot.com"

    logo_url            = db.Column(db.String(500))

    # Cached scores — recalculated after every query run batch
    # Stored here so dashboard reads are instant (no heavy query on load)
    ai_visibility_score = db.Column(db.Float, default=0.0)
    # 0-100: % of monitored queries where brand was mentioned this week

    accuracy_score      = db.Column(db.Float, default=0.0)
    # 0-100: % of AI responses with all facts correct this week

    top_rec_rate        = db.Column(db.Float, default=0.0)
    # 0-100: % of queries where brand is position #1 recommendation

    open_error_count    = db.Column(db.Integer, default=0)
    # Count of active unresolved FactualErrors — shown as badge on dashboard

    bot_allowed         = db.Column(db.Boolean, default=True)
    # False = GPTBot blocked in robots.txt — critical error flag

    last_crawled_at     = db.Column(db.DateTime)
    last_queried_at     = db.Column(db.DateTime)
    created_at          = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    query_templates = db.relationship("QueryTemplate",   back_populates="company", cascade="all, delete-orphan")
    query_runs      = db.relationship("QueryRun",        back_populates="company", cascade="all, delete-orphan")
    crawl_jobs      = db.relationship("CrawlJob",        back_populates="company", cascade="all, delete-orphan")
    competitors     = db.relationship("Competitor",      back_populates="company", cascade="all, delete-orphan")
    content_fixes   = db.relationship("ContentFix",      back_populates="company", cascade="all, delete-orphan")
    ethics_flags    = db.relationship("EthicsFlag",      back_populates="company", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Company {self.name}>"

    def to_dict(self):
        return {
            "id":                   self.id,
            "name":                 self.name,
            "slug":                 self.slug,
            "industry_type":        self.industry_type.value,
            "primary_domain":       self.primary_domain,
            "logo_url":             self.logo_url,
            "ai_visibility_score":  self.ai_visibility_score,
            "accuracy_score":       self.accuracy_score,
            "top_rec_rate":         self.top_rec_rate,
            "open_error_count":     self.open_error_count,
            "bot_allowed":          self.bot_allowed,
            "last_crawled_at":      self.last_crawled_at.isoformat() if self.last_crawled_at else None,
            "last_queried_at":      self.last_queried_at.isoformat() if self.last_queried_at else None,
            "created_at":           self.created_at.isoformat() if self.created_at else None,
        }


class CompanyConfig(db.Model):
    """
    Optional per-company configuration overrides.
    Stores things like which LLM platforms to query,
    which pages to prioritize for crawling, and custom
    compliance rules for regulated industries.
    """
    __tablename__ = "company_configs"

    id                     = db.Column(db.Integer, primary_key=True)
    company_id             = db.Column(db.Integer, db.ForeignKey("companies.id"), unique=True, nullable=False)
    # unique=True: one config per company (one-to-one)

    enabled_platforms      = db.Column(db.JSON, default=lambda: ["chatgpt", "gemini", "perplexity", "claude"])
    # List of LLMPlatform values to query. Default: all 4 platforms.

    priority_pages         = db.Column(db.JSON, default=list)
    # List of URLs to always crawl first. Override the default crawl order.

    compliance_mode        = db.Column(db.Boolean, default=False)
    # True for financial companies — enables strict ethics flagging
    # and auto-alerts to legal when compliance_risk errors are found.

    alert_email            = db.Column(db.String(255))
    # Where to send compliance alerts and weekly summary emails.

    query_frequency_hours  = db.Column(db.Integer, default=24)
    # How often to run query batches. Default 24 hrs. Can be lowered to 12.

    crawl_frequency_days   = db.Column(db.Integer, default=7)
    # How often to crawl the website. Default 7 days.

    created_at             = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at             = db.Column(db.DateTime, onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    company = db.relationship("Company", backref=db.backref("config", uselist=False))

    def __repr__(self):
        return f"<CompanyConfig company_id={self.company_id}>"
