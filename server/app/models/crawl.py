from app.extensions import db
from datetime import datetime, timezone
import enum


class CrawlStatus(enum.Enum):
    PENDING    = "pending"
    RUNNING    = "running"
    COMPLETED  = "completed"
    PARTIAL    = "partial"    # Some pages failed but job finished
    FAILED     = "failed"


class PageType(enum.Enum):
    PRODUCT_PAGE   = "product_page"
    CATEGORY_PAGE  = "category_page"
    LANDING_PAGE   = "landing_page"
    FAQ_PAGE       = "faq_page"
    POLICY_PAGE    = "policy_page"
    BLOG_POST      = "blog_post"
    COMPARISON     = "comparison"
    HOMEPAGE       = "homepage"


class SchemaIssueType(enum.Enum):
    MISSING_TYPE      = "missing_type"       # No @type field in JSON-LD
    MISSING_FIELD     = "missing_field"      # Required field absent (e.g. name, price)
    INVALID_VALUE     = "invalid_value"      # Field present but wrong format or value
    OUTDATED_PRICE    = "outdated_price"     # Price in schema doesn't match page content
    DUPLICATE_SCHEMA  = "duplicate_schema"   # Multiple conflicting schema blocks on same page
    WRONG_TYPE        = "wrong_type"         # Wrong schema type for this kind of page


class CrawlJob(db.Model):
    """
    One full website crawl run for a company.
    Vigil crawls every important product page weekly, mimicking
    exactly what GPTBot does — no JavaScript, raw HTML only.
    CrawlJob is the parent record; PageAudit is one page per crawl.
    """
    __tablename__ = "crawl_jobs"

    id             = db.Column(db.Integer, primary_key=True)
    company_id     = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    status         = db.Column(db.Enum(CrawlStatus), default=CrawlStatus.PENDING)

    pages_found    = db.Column(db.Integer, default=0)
    # Total pages discovered during the crawl (from sitemap + link follow)

    pages_crawled  = db.Column(db.Integer, default=0)
    # Pages successfully fetched and audited

    pages_failed   = db.Column(db.Integer, default=0)
    # Pages that returned errors (4xx, 5xx, timeout)

    bot_blocked    = db.Column(db.Boolean, default=False)
    # True if robots.txt disallows GPTBot on any page during this crawl
    # Synced back to Company.bot_allowed after crawl completes

    error_message  = db.Column(db.Text)
    # Populated if status = FAILED (e.g. sitemap fetch failed)

    started_at     = db.Column(db.DateTime)
    completed_at   = db.Column(db.DateTime)
    created_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    company     = db.relationship("Company", back_populates="crawl_jobs")
    page_audits = db.relationship("PageAudit", back_populates="crawl_job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<CrawlJob id={self.id} company_id={self.company_id} status={self.status.value}>"

    def to_dict(self):
        return {
            "id":            self.id,
            "company_id":    self.company_id,
            "status":        self.status.value,
            "pages_found":   self.pages_found,
            "pages_crawled": self.pages_crawled,
            "pages_failed":  self.pages_failed,
            "bot_blocked":   self.bot_blocked,
            "started_at":    self.started_at.isoformat() if self.started_at else None,
            "completed_at":  self.completed_at.isoformat() if self.completed_at else None,
        }


class PageAudit(db.Model):
    """
    The audit result for one specific URL during a crawl.
    This is the most detailed technical record — it answers:
    "what can AI actually see on this page right now?"

    The gap between bot_readable_text and human_readable_text
    is the root cause of most hallucinations. Large deltas mean
    the page relies on JavaScript to show key content, which AI
    bots cannot execute.
    """
    __tablename__ = "page_audits"

    id                    = db.Column(db.Integer, primary_key=True)
    crawl_job_id          = db.Column(db.Integer, db.ForeignKey("crawl_jobs.id"), nullable=False)
    company_id            = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    url                   = db.Column(db.String(1000), nullable=False)
    page_type             = db.Column(db.Enum(PageType))

    # Bot-perspective vs human-perspective content
    bot_readable_text     = db.Column(db.Text)
    # Text extracted with NO JavaScript execution — what GPTBot sees
    # Fetched via plain httpx GET (no browser rendering)

    human_readable_text   = db.Column(db.Text)
    # Text extracted WITH JavaScript rendered — what a browser user sees
    # Fetched via headless browser (Playwright/Selenium)

    content_delta         = db.Column(db.Text)
    # Diff between bot text and human text — the JS-hidden content gap
    # Stored as plain text description of what's missing

    content_delta_score   = db.Column(db.Float, default=0.0)
    # 0.0 = identical (no gap), 1.0 = completely different (nothing visible to bot)
    # Calculated as 1 - (overlap / max_length)

    # Schema markup analysis
    has_schema            = db.Column(db.Boolean, default=False)
    # True if JSON-LD or microdata schema was found on the page

    has_valid_schema      = db.Column(db.Boolean, default=False)
    # True if schema is present AND passes validation (no missing required fields)

    schema_types_found    = db.Column(db.JSON, default=list)
    # List of @type values found — e.g. ["Product", "BreadcrumbList"]

    # Crawl metadata
    http_status           = db.Column(db.Integer)
    # HTTP response code — 200, 404, 403, 500, etc.

    response_time_ms      = db.Column(db.Integer)
    # How long the bot-perspective fetch took

    word_count_bot        = db.Column(db.Integer, default=0)
    # Word count of bot_readable_text

    word_count_human      = db.Column(db.Integer, default=0)
    # Word count of human_readable_text

    crawled_at            = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    crawl_job     = db.relationship("CrawlJob", back_populates="page_audits")
    schema_issues = db.relationship("SchemaIssue", back_populates="page_audit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PageAudit id={self.id} url={self.url[:50]}>"

    def to_dict(self):
        return {
            "id":                  self.id,
            "crawl_job_id":        self.crawl_job_id,
            "url":                 self.url,
            "page_type":           self.page_type.value if self.page_type else None,
            "has_schema":          self.has_schema,
            "has_valid_schema":    self.has_valid_schema,
            "schema_types_found":  self.schema_types_found,
            "content_delta_score": self.content_delta_score,
            "http_status":         self.http_status,
            "word_count_bot":      self.word_count_bot,
            "word_count_human":    self.word_count_human,
            "crawled_at":          self.crawled_at.isoformat() if self.crawled_at else None,
        }


class SchemaIssue(db.Model):
    """
    One specific problem found in a page's schema markup.
    Stored separately from PageAudit because one page can have
    multiple schema issues, and each needs its own description and generated fix.
    """
    __tablename__ = "schema_issues"

    id              = db.Column(db.Integer, primary_key=True)
    page_audit_id   = db.Column(db.Integer, db.ForeignKey("page_audits.id"), nullable=False)

    issue_type      = db.Column(db.Enum(SchemaIssueType), nullable=False)

    field_path      = db.Column(db.String(255))
    # JSON path to the problematic field — e.g. "Product.offers.price"

    current_value   = db.Column(db.Text)
    # What the schema currently says (null if field is missing)

    expected_value  = db.Column(db.Text)
    # What it should say, or a description of what is required

    description     = db.Column(db.Text)
    # Human-readable explanation of the issue shown in the readability audit UI

    auto_fixable    = db.Column(db.Boolean, default=False)
    # True if Vigil can auto-generate the corrected JSON-LD block

    created_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    page_audit = db.relationship("PageAudit", back_populates="schema_issues")

    def __repr__(self):
        return f"<SchemaIssue id={self.id} type={self.issue_type.value}>"

    def to_dict(self):
        return {
            "id":            self.id,
            "page_audit_id": self.page_audit_id,
            "issue_type":    self.issue_type.value,
            "field_path":    self.field_path,
            "current_value": self.current_value,
            "expected_value":self.expected_value,
            "description":   self.description,
            "auto_fixable":  self.auto_fixable,
        }
