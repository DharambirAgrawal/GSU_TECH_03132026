from app.extensions import db
from datetime import datetime, timezone
import enum


class QueryCategory(enum.Enum):
    PRODUCT_RECOMMENDATION = "product_recommendation"
    # "best drill under $200"
    PRODUCT_FACT           = "product_fact"
    # "what is the price of Milwaukee M18"
    COMPETITOR_COMPARISON  = "competitor_comparison"
    # "Home Depot vs Lowe's for lumber"
    POLICY_QUESTION        = "policy_question"
    # "what is Home Depot's return policy"
    BRAND_GENERAL          = "brand_general"
    # "tell me about Capital One credit cards"
    USE_CASE               = "use_case"
    # "what tools do I need to tile a bathroom"


class LLMPlatform(enum.Enum):
    CHATGPT    = "chatgpt"
    GEMINI     = "gemini"
    PERPLEXITY = "perplexity"
    CLAUDE     = "claude"


class RunStatus(enum.Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    FAILED    = "failed"


class QueryTemplate(db.Model):
    """
    Library of reusable questions available for manual runs.
    Frontend can ask for N prompts for a product/topic, allow user edits,
    then execute those prompts in a user-triggered batch.
    """
    __tablename__ = "query_templates"

    id                     = db.Column(db.Integer, primary_key=True)
    company_id             = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    query_text             = db.Column(db.Text, nullable=False)
    # The actual question sent to AI platforms
    # e.g. "What is the best cordless drill under $200 for a beginner?"

    category               = db.Column(db.Enum(QueryCategory), nullable=False)
    # Groups queries for accuracy breakdown chart on dashboard

    priority               = db.Column(db.Integer, default=5)
    # 1 = highest priority, 10 = lowest
    # Used to order execution when rate limits hit

    expected_brand_mention = db.Column(db.Boolean, default=True)
    # True = brand SHOULD appear in the AI answer for this query.
    # Queries where they should be mentioned but aren't = serious gaps.

    is_active              = db.Column(db.Boolean, default=True)
    # Inactive templates are hidden from prompt suggestion and batch generation.

    created_at             = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    company    = db.relationship("Company", back_populates="query_templates")
    query_runs = db.relationship("QueryRun", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QueryTemplate id={self.id} category={self.category.value}>"

    def to_dict(self):
        return {
            "id":                     self.id,
            "company_id":             self.company_id,
            "query_text":             self.query_text,
            "category":               self.category.value,
            "priority":               self.priority,
            "expected_brand_mention": self.expected_brand_mention,
            "is_active":              self.is_active,
            "created_at":             self.created_at.isoformat() if self.created_at else None,
        }


class QueryRun(db.Model):
    """
    One execution of one QueryTemplate against one AI platform.
    Runs are no longer scheduler-driven; they are created by explicit
    user-initiated batch requests from the frontend.
    """
    __tablename__ = "query_runs"

    id                  = db.Column(db.Integer, primary_key=True)
    company_id          = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    template_id         = db.Column(db.Integer, db.ForeignKey("query_templates.id"), nullable=False)
    batch_run_id        = db.Column(db.Integer, db.ForeignKey("query_batch_runs.id"))
    batch_item_id       = db.Column(db.Integer, db.ForeignKey("query_batch_items.id"))
    # Links each run back to a manual history entry for "what happened last time" views.

    platform            = db.Column(db.Enum(LLMPlatform), nullable=False)
    status              = db.Column(db.Enum(RunStatus), default=RunStatus.PENDING)

    raw_response        = db.Column(db.Text)
    # Full text of what the AI said — stored for fact-checking

    brand_mentioned     = db.Column(db.Boolean)
    # Was the company mentioned anywhere in the response?

    brand_position      = db.Column(db.Integer)
    # 1 = recommended first, 2 = second, null = not mentioned

    citations_found     = db.Column(db.JSON)
    # List of URLs/sources the AI cited in its response
    # e.g. ["nerdwallet.com/article/...", "reddit.com/r/..."]

    response_latency_ms = db.Column(db.Integer)
    # Time in ms for the AI to respond — helps detect degraded platforms

    error_message       = db.Column(db.Text)
    # Populated if status = FAILED

    ran_at              = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    company        = db.relationship("Company", back_populates="query_runs")
    template       = db.relationship("QueryTemplate", back_populates="query_runs")
    accuracy_check = db.relationship("AccuracyCheck", back_populates="query_run", uselist=False)
    # uselist=False enforces one-to-one: one query run → one accuracy check

    def __repr__(self):
        return f"<QueryRun id={self.id} platform={self.platform.value} status={self.status.value}>"

    def to_dict(self):
        return {
            "id":                   self.id,
            "company_id":           self.company_id,
            "template_id":          self.template_id,
            "platform":             self.platform.value,
            "status":               self.status.value,
            "brand_mentioned":      self.brand_mentioned,
            "brand_position":       self.brand_position,
            "citations_found":      self.citations_found,
            "response_latency_ms":  self.response_latency_ms,
            "error_message":        self.error_message,
            "ran_at":               self.ran_at.isoformat() if self.ran_at else None,
        }


class QueryResult(db.Model):
    """
    Aggregated statistics computed from multiple QueryRuns for a template
    or from a specific manual batch run.
    Stored separately so dashboard charts can load fast without
    re-aggregating hundreds of QueryRun rows on every request.
    Updated after each manual batch completes.
    """
    __tablename__ = "query_results"

    id                  = db.Column(db.Integer, primary_key=True)
    template_id         = db.Column(db.Integer, db.ForeignKey("query_templates.id"), nullable=False)
    company_id          = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    period_start        = db.Column(db.DateTime, nullable=False)
    period_end          = db.Column(db.DateTime, nullable=False)
    # The time window this aggregation covers (usually 7 days)

    total_runs          = db.Column(db.Integer, default=0)
    # Total QueryRun rows in this period for this template

    mention_count       = db.Column(db.Integer, default=0)
    # How many runs had brand_mentioned = True

    mention_rate        = db.Column(db.Float, default=0.0)
    # mention_count / total_runs * 100 — the primary visibility metric

    avg_position        = db.Column(db.Float)
    # Average brand_position across runs where brand was mentioned

    top_position_count  = db.Column(db.Integer, default=0)
    # How many runs had brand_position = 1

    computed_at         = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    template = db.relationship("QueryTemplate", backref="results")
    company  = db.relationship("Company")

    def __repr__(self):
        return f"<QueryResult template={self.template_id} mention_rate={self.mention_rate}>"
