from app.extensions import db
from datetime import datetime, timezone
import enum


class FixType(enum.Enum):
    USE_CASE_BLOCK     = "use_case_block"
    # New FAQ/use-case content block answering a specific query gap

    SCHEMA_PATCH       = "schema_patch"
    # Complete corrected JSON-LD schema block ready to drop into the page

    FACT_CORRECTION    = "fact_correction"
    # Updated copy correcting wrong facts on an existing page

    NEW_PAGE           = "new_page"
    # Full new page draft (HTML + copy) to fill a content gap

    META_UPDATE        = "meta_update"
    # Updated title tag, meta description, and H1 for better AI pickup

    ROBOTS_INSTRUCTION = "robots_instruction"
    # robots.txt change instruction to allow GPTBot on blocked pages
    # (Not actual content but still a discrete fix that needs review)


class FixStatus(enum.Enum):
    GENERATED  = "generated"   # AI wrote it, not yet reviewed
    APPROVED   = "approved"    # Human reviewer approved it
    PUBLISHED  = "published"   # Live on the website
    REJECTED   = "rejected"    # Human reviewer rejected it
    SUPERSEDED = "superseded"  # A newer fix replaced this one


class ContentFix(db.Model):
    """
    An auto-generated piece of content that fixes a specific FactualError
    or content gap. Core differentiator — not just flagging problems but
    generating the fix ready for review and publishing.
    """
    __tablename__ = "content_fixes"

    id                  = db.Column(db.Integer, primary_key=True)
    company_id          = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    factual_error_id    = db.Column(db.Integer, db.ForeignKey("factual_errors.id"), nullable=True)
    # Null if this fix addresses a content gap (not a specific error)

    fix_type            = db.Column(db.Enum(FixType), nullable=False)
    status              = db.Column(db.Enum(FixStatus), default=FixStatus.GENERATED)

    title               = db.Column(db.String(255))
    # Short descriptive title shown in the Action Center
    # e.g. "Fix APR misinformation — add schema to credit card page"

    generated_content   = db.Column(db.Text)
    # The actual ready-to-publish content.
    # For SCHEMA_PATCH: JSON-LD block
    # For USE_CASE_BLOCK: HTML content block
    # For FACT_CORRECTION: updated copy with tracked changes
    # For NEW_PAGE: full HTML page draft
    # For META_UPDATE: title + meta description + H1 recommendations
    # For ROBOTS_INSTRUCTION: diff showing robots.txt change

    target_page_url     = db.Column(db.String(1000))
    # Which page on the company site this fix should be applied to

    target_queries      = db.Column(db.JSON, default=list)
    # List of QueryTemplate IDs this fix is intended to improve
    # Used after publishing to measure if visibility improved

    estimated_impact    = db.Column(db.Float, default=0.0)
    # 0.0-1.0 score predicted by content_generator.py
    # Higher = fixing this will improve visibility/accuracy scores more
    # Used to sort the Action Center queue

    effort_level        = db.Column(db.String(20), default="medium")
    # "low", "medium", "high" — estimated publishing effort
    # low = paste a schema block, high = publish a new page

    # Before/after score tracking (populated after 30 days post-publish)
    before_score        = db.Column(db.Float)
    # Company's accuracy or visibility score BEFORE this fix was published

    after_score         = db.Column(db.Float)
    # Score AFTER fix has been live 30 days — proves ROI

    # Lifecycle timestamps
    generated_at        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    approved_at         = db.Column(db.DateTime)
    published_at        = db.Column(db.DateTime)
    reviewed_by         = db.Column(db.String(100))
    # Email or name of the human who approved/rejected

    review_notes        = db.Column(db.Text)
    # Optional notes from the reviewer

    # Relationships
    company       = db.relationship("Company", back_populates="content_fixes")
    factual_error = db.relationship("FactualError", back_populates="content_fix")

    def __repr__(self):
        return f"<ContentFix id={self.id} type={self.fix_type.value} status={self.status.value}>"

    def to_dict(self):
        return {
            "id":               self.id,
            "company_id":       self.company_id,
            "factual_error_id": self.factual_error_id,
            "fix_type":         self.fix_type.value,
            "status":           self.status.value,
            "title":            self.title,
            "target_page_url":  self.target_page_url,
            "target_queries":   self.target_queries,
            "estimated_impact": self.estimated_impact,
            "effort_level":     self.effort_level,
            "before_score":     self.before_score,
            "after_score":      self.after_score,
            "generated_at":     self.generated_at.isoformat() if self.generated_at else None,
            "published_at":     self.published_at.isoformat() if self.published_at else None,
        }


class PublishedFix(db.Model):
    """
    Immutable record of a ContentFix after it goes live.
    Keeps a permanent snapshot of what was published, when,
    and what impact it had — for the audit trail and ROI reporting.
    """
    __tablename__ = "published_fixes"

    id                = db.Column(db.Integer, primary_key=True)
    content_fix_id    = db.Column(db.Integer, db.ForeignKey("content_fixes.id"), nullable=False)
    company_id        = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    published_content = db.Column(db.Text)
    # Snapshot of the content exactly as published (in case fix is later edited)

    published_at      = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    published_by      = db.Column(db.String(100))

    impact_measured   = db.Column(db.Boolean, default=False)
    # True once 30-day post-publish score has been measured

    score_delta       = db.Column(db.Float)
    # after_score - before_score — the proven improvement

    measurement_notes = db.Column(db.Text)

    # Relationships
    content_fix = db.relationship("ContentFix", backref="published_record")

    def __repr__(self):
        return f"<PublishedFix id={self.id} fix={self.content_fix_id}>"
