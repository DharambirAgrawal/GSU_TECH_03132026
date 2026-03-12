import enum
from datetime import datetime, timezone

from app.extensions import db


class BatchStatus(enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class BatchSource(enum.Enum):
    MANUAL = "manual"


class QueryBatchRun(db.Model):
    """
    Parent record for a user-triggered run from frontend.
    Represents one historical execution event that users can revisit
    to compare progress over time.
    """

    __tablename__ = "query_batch_runs"

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("company_users.id"), nullable=False)

    source = db.Column(db.Enum(BatchSource), default=BatchSource.MANUAL)
    product_topic = db.Column(db.String(255), nullable=False)
    # Example: "Laptop", "Cordless Drill", "Travel Card"

    requested_query_count = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(BatchStatus), default=BatchStatus.QUEUED)

    total_queries = db.Column(db.Integer, default=0)
    completed_queries = db.Column(db.Integer, default=0)
    failed_queries = db.Column(db.Integer, default=0)

    before_snapshot = db.Column(db.JSON)
    after_snapshot = db.Column(db.JSON)
    # Score snapshots used for historical comparison in dashboard history.

    summary_payload = db.Column(db.JSON)
    error_message = db.Column(db.Text)

    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    company = db.relationship("Company", back_populates="query_batches")
    created_by = db.relationship("CompanyUser", back_populates="created_runs")
    items = db.relationship("QueryBatchItem", back_populates="batch_run", cascade="all, delete-orphan")


class BatchItemStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class QueryBatchItem(db.Model):
    """
    One query prompt inside a batch run.
    Supports frontend editing of generated prompts before starting.
    """

    __tablename__ = "query_batch_items"

    id = db.Column(db.Integer, primary_key=True)
    batch_run_id = db.Column(db.Integer, db.ForeignKey("query_batch_runs.id"), nullable=False)
    company_id = db.Column(db.Integer, db.ForeignKey("companies.id"), nullable=False)

    template_id = db.Column(db.Integer, db.ForeignKey("query_templates.id"))
    # Optional link to a reusable template.

    query_text = db.Column(db.Text, nullable=False)
    edited_by_user_id = db.Column(db.Integer, db.ForeignKey("company_users.id"))
    prompt_order = db.Column(db.Integer, default=0)

    status = db.Column(db.Enum(BatchItemStatus), default=BatchItemStatus.PENDING)
    item_summary = db.Column(db.JSON)
    item_error_message = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)

    batch_run = db.relationship("QueryBatchRun", back_populates="items")
    company = db.relationship("Company")
    template = db.relationship("QueryTemplate")
    edited_by = db.relationship("CompanyUser")
