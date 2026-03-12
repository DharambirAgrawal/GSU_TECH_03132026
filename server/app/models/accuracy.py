from app.extensions import db
from datetime import datetime, timezone
import enum


class ErrorType(enum.Enum):
    WRONG_PRICE          = "wrong_price"
    WRONG_SPEC           = "wrong_spec"
    WRONG_POLICY         = "wrong_policy"
    WRONG_AVAILABILITY   = "wrong_availability"
    WRONG_REWARDS        = "wrong_rewards"
    DISCONTINUED_PRODUCT = "discontinued_product"
    WRONG_FEE            = "wrong_fee"
    HALLUCINATED_FEATURE = "hallucinated_feature"


class ErrorSeverity(enum.Enum):
    CRITICAL = "critical"   # Wrong price, APR, fee — consumer harm possible
    HIGH     = "high"       # Wrong spec, discontinued product
    MEDIUM   = "medium"     # Wrong minor detail, small inaccuracy
    LOW      = "low"        # Outdated but harmless information


class RootCause(enum.Enum):
    JS_HIDDEN_CONTENT = "js_hidden_content"
    # AI bot could not read because content loads via JavaScript

    INVALID_SCHEMA    = "invalid_schema"
    # Schema markup exists but is malformed — AI ignored it

    MISSING_SCHEMA    = "missing_schema"
    # No schema markup at all on the relevant page

    THIRD_PARTY_SOURCE = "third_party_source"
    # AI trusted NerdWallet/Reddit over the company's own page

    STALE_CONTENT     = "stale_content"
    # Page exists and is readable but information is outdated

    BOT_BLOCKED       = "bot_blocked"
    # GPTBot was blocked from this page in robots.txt

    CONTENT_GAP       = "content_gap"
    # Company simply doesn't have content covering this query

    TRAINING_DATA     = "training_data"
    # Error in AI's training data — hardest to fix directly


class AccuracyCheck(db.Model):
    """
    Result of the fact-checking step for one QueryRun.
    After the AI responds, Vigil fetches the company's live page
    and compares every factual claim in the AI response against it.
    This is the core of the ethics layer.
    """
    __tablename__ = "accuracy_checks"

    id             = db.Column(db.Integer, primary_key=True)
    query_run_id   = db.Column(db.Integer, db.ForeignKey("query_runs.id"), unique=True, nullable=False)
    # unique=True enforces one-to-one with QueryRun

    live_page_url  = db.Column(db.String(500))
    # Which company page was fetched as the source of truth

    live_page_snapshot = db.Column(db.Text)
    # The actual extracted text content of that page at check time
    # NOT the full HTML — just the facts in plain text

    claims_checked = db.Column(db.Integer, default=0)
    # Total number of factual statements extracted from the AI response

    claims_correct = db.Column(db.Integer, default=0)
    # How many of those claims matched the live page

    claims_wrong   = db.Column(db.Integer, default=0)
    # How many claims were contradicted by the live page

    overall_accurate = db.Column(db.Boolean)
    # True only if ALL claims were correct (claims_wrong == 0)
    # This boolean is the input used by scoring.py for accuracy score

    checked_at     = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    query_run      = db.relationship("QueryRun", back_populates="accuracy_check")
    factual_errors = db.relationship("FactualError", back_populates="accuracy_check", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AccuracyCheck id={self.id} accurate={self.overall_accurate}>"

    def accuracy_percentage(self):
        # Helper: returns percentage of correct claims (0 if none checked)
        if self.claims_checked == 0:
            return 0.0
        return round((self.claims_correct / self.claims_checked) * 100, 2)

    def to_dict(self):
        return {
            "id":                self.id,
            "query_run_id":      self.query_run_id,
            "live_page_url":     self.live_page_url,
            "claims_checked":    self.claims_checked,
            "claims_correct":    self.claims_correct,
            "claims_wrong":      self.claims_wrong,
            "overall_accurate":  self.overall_accurate,
            "accuracy_pct":      self.accuracy_percentage(),
            "checked_at":        self.checked_at.isoformat() if self.checked_at else None,
        }


class FactualError(db.Model):
    """
    One specific wrong fact found in one AI response.
    Powers the Error Log tab on the dashboard.
    Every error has a root cause, a severity, and optionally a ContentFix.
    """
    __tablename__ = "factual_errors"

    id                   = db.Column(db.Integer, primary_key=True)
    accuracy_check_id    = db.Column(db.Integer, db.ForeignKey("accuracy_checks.id"), nullable=False)
    company_id           = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    error_type           = db.Column(db.Enum(ErrorType), nullable=False)
    severity             = db.Column(db.Enum(ErrorSeverity), nullable=False)

    # Side-by-side comparison fields shown in the error log UI
    field_name           = db.Column(db.String(100))
    # e.g. "APR", "price", "annual_fee", "RAM", "return_policy_days"

    ai_stated_value      = db.Column(db.Text)
    # What the AI said — e.g. "19.99% variable APR"

    correct_value        = db.Column(db.Text)
    # What is actually true — e.g. "24.99% variable APR (as of January 2026)"

    source_page_url      = db.Column(db.String(500))
    # The live company page where the correct value was found

    # Root cause diagnosis (set by services/root_cause.py)
    root_cause           = db.Column(db.Enum(RootCause))
    root_cause_detail    = db.Column(db.Text)
    # Plain English explanation shown in the error log
    # e.g. "NerdWallet article from 2023 still says 19.99% and ranks above your own page"

    third_party_source   = db.Column(db.String(255))
    # If root_cause = THIRD_PARTY_SOURCE, which site is it?
    # e.g. "nerdwallet.com"

    # Resolution tracking
    is_resolved          = db.Column(db.Boolean, default=False)
    resolved_at          = db.Column(db.DateTime)
    resolution_note      = db.Column(db.Text)
    # Free-text note about how it was resolved

    # Ethics / compliance layer
    compliance_risk      = db.Column(db.Boolean, default=False)
    # True for financial companies when pricing/terms are wrong
    # Triggers compliance alert workflow

    compliance_flag_sent = db.Column(db.Boolean, default=False)
    # True once the legal/compliance team has been alerted via email

    occurrence_count     = db.Column(db.Integer, default=1)
    # How many times this exact error has been seen across all runs
    # Incremented each time the same issue recurs in later manual runs

    first_seen_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    accuracy_check = db.relationship("AccuracyCheck", back_populates="factual_errors")
    content_fix    = db.relationship("ContentFix", back_populates="factual_error", uselist=False)
    # Each error can have at most one auto-generated fix (one-to-one)

    def __repr__(self):
        return f"<FactualError id={self.id} type={self.error_type.value} severity={self.severity.value}>"

    def to_dict(self):
        return {
            "id":                  self.id,
            "accuracy_check_id":   self.accuracy_check_id,
            "company_id":          self.company_id,
            "error_type":          self.error_type.value,
            "severity":            self.severity.value,
            "field_name":          self.field_name,
            "ai_stated_value":     self.ai_stated_value,
            "correct_value":       self.correct_value,
            "source_page_url":     self.source_page_url,
            "root_cause":          self.root_cause.value if self.root_cause else None,
            "root_cause_detail":   self.root_cause_detail,
            "third_party_source":  self.third_party_source,
            "is_resolved":         self.is_resolved,
            "resolved_at":         self.resolved_at.isoformat() if self.resolved_at else None,
            "compliance_risk":     self.compliance_risk,
            "compliance_flag_sent":self.compliance_flag_sent,
            "occurrence_count":    self.occurrence_count,
            "first_seen_at":       self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_seen_at":        self.last_seen_at.isoformat() if self.last_seen_at else None,
        }
