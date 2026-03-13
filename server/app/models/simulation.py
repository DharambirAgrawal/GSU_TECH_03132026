from datetime import datetime, timezone
import uuid

from app.extensions import db


def _uuid_str() -> str:
    return str(uuid.uuid4())


class Simulation(db.Model):
    __tablename__ = "simulations"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    company_id = db.Column(
        db.Integer, db.ForeignKey("companies.id"), nullable=False, index=True
    )
    company_user_id = db.Column(
        db.Integer, db.ForeignKey("company_users.id"), nullable=False, index=True
    )

    time_started = db.Column(db.DateTime, nullable=False)
    time_ended = db.Column(db.DateTime)
    status = db.Column(db.String(20), nullable=False, default="queued")

    product_specification = db.Column(db.Text, nullable=False)
    n_iteration = db.Column(db.Integer, nullable=False)
    additional_detail = db.Column(db.Text)

    about_company = db.Column(db.Text)
    contact_email = db.Column(db.String(320))
    url = db.Column(db.String(1000))

    time_created = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    company = db.relationship("Company", back_populates="simulations")
    company_user = db.relationship("CompanyUser", back_populates="created_simulations")
    prompts = db.relationship(
        "Prompt", back_populates="simulation", cascade="all, delete-orphan"
    )
    model_runs = db.relationship(
        "PromptModelRun", back_populates="simulation", cascade="all, delete-orphan"
    )
    citations = db.relationship(
        "Citation", back_populates="simulation", cascade="all, delete-orphan"
    )
    errors = db.relationship(
        "Error", back_populates="simulation", cascade="all, delete-orphan"
    )
    fact_checks = db.relationship(
        "FactCheck", back_populates="simulation", cascade="all, delete-orphan"
    )
    report_summary = db.relationship(
        "ReportSummary",
        back_populates="simulation",
        uselist=False,
        cascade="all, delete-orphan",
    )


class Prompt(db.Model):
    __tablename__ = "prompts"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    simulation_id = db.Column(
        db.String(36), db.ForeignKey("simulations.id"), nullable=False, index=True
    )

    text = db.Column(db.Text, nullable=False)
    prompt_order = db.Column(db.Integer, nullable=False, default=0)
    time_created = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    simulation = db.relationship("Simulation", back_populates="prompts")
    model_runs = db.relationship(
        "PromptModelRun", back_populates="prompt", cascade="all, delete-orphan"
    )
    citations = db.relationship(
        "Citation", back_populates="prompt", cascade="all, delete-orphan"
    )
    errors = db.relationship(
        "Error", back_populates="prompt", cascade="all, delete-orphan"
    )
    fact_checks = db.relationship(
        "FactCheck", back_populates="prompt", cascade="all, delete-orphan"
    )


class PromptModelRun(db.Model):
    __tablename__ = "prompt_model_runs"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    simulation_id = db.Column(
        db.String(36), db.ForeignKey("simulations.id"), nullable=False, index=True
    )
    prompt_id = db.Column(
        db.String(36), db.ForeignKey("prompts.id"), nullable=False, index=True
    )

    model_name = db.Column(db.String(64), nullable=False)
    success_or_failed = db.Column(db.String(20), nullable=False, default="success")
    failure_reason = db.Column(db.Text)
    mitigation = db.Column(db.Text)

    citations_found_count = db.Column(db.Integer, nullable=False, default=0)
    dead_links_count = db.Column(db.Integer, nullable=False, default=0)
    fact_score = db.Column(db.Float)
    fact_score_reason = db.Column(db.Text)

    time_created = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    simulation = db.relationship("Simulation", back_populates="model_runs")
    prompt = db.relationship("Prompt", back_populates="model_runs")
    citations = db.relationship(
        "Citation", back_populates="run", cascade="all, delete-orphan"
    )
    errors = db.relationship(
        "Error", back_populates="run", cascade="all, delete-orphan"
    )
    fact_checks = db.relationship(
        "FactCheck", back_populates="run", cascade="all, delete-orphan"
    )


class Citation(db.Model):
    __tablename__ = "citations"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    simulation_id = db.Column(
        db.String(36), db.ForeignKey("simulations.id"), nullable=False, index=True
    )
    prompt_id = db.Column(
        db.String(36), db.ForeignKey("prompts.id"), nullable=False, index=True
    )
    run_id = db.Column(
        db.String(36), db.ForeignKey("prompt_model_runs.id"), nullable=False, index=True
    )

    company_cited = db.Column(db.String(255), nullable=False)
    website_domain = db.Column(db.String(255), nullable=False)
    cited_url = db.Column(db.String(2000), nullable=False)
    model_name = db.Column(db.String(64), nullable=False)

    time_created = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    simulation = db.relationship("Simulation", back_populates="citations")
    prompt = db.relationship("Prompt", back_populates="citations")
    run = db.relationship("PromptModelRun", back_populates="citations")


class Error(db.Model):
    __tablename__ = "errors"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    simulation_id = db.Column(
        db.String(36), db.ForeignKey("simulations.id"), nullable=False, index=True
    )
    prompt_id = db.Column(
        db.String(36), db.ForeignKey("prompts.id"), nullable=False, index=True
    )
    run_id = db.Column(
        db.String(36), db.ForeignKey("prompt_model_runs.id"), nullable=False, index=True
    )

    company_link = db.Column(db.String(2000))
    error_type = db.Column(db.String(100), nullable=False)
    severity = db.Column(db.String(20), nullable=False, default="medium")
    reason_for_failure = db.Column(db.Text, nullable=False)
    mitigation = db.Column(db.Text, nullable=False)
    model_name = db.Column(db.String(64), nullable=False)

    time_created = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    simulation = db.relationship("Simulation", back_populates="errors")
    prompt = db.relationship("Prompt", back_populates="errors")
    run = db.relationship("PromptModelRun", back_populates="errors")


class FactCheck(db.Model):
    __tablename__ = "fact_checks"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    simulation_id = db.Column(
        db.String(36), db.ForeignKey("simulations.id"), nullable=False, index=True
    )
    prompt_id = db.Column(
        db.String(36), db.ForeignKey("prompts.id"), nullable=False, index=True
    )
    run_id = db.Column(
        db.String(36), db.ForeignKey("prompt_model_runs.id"), nullable=False, index=True
    )

    company_link = db.Column(db.String(2000))
    ai_text_about = db.Column(db.Text, nullable=False)
    fact_score = db.Column(db.Float, nullable=False)
    reason_for_score = db.Column(db.Text, nullable=False)
    mitigation = db.Column(db.Text, nullable=False)
    model_name = db.Column(db.String(64), nullable=False)

    time_created = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    simulation = db.relationship("Simulation", back_populates="fact_checks")
    prompt = db.relationship("Prompt", back_populates="fact_checks")
    run = db.relationship("PromptModelRun", back_populates="fact_checks")


class ReportSummary(db.Model):
    __tablename__ = "report_summaries"

    id = db.Column(db.String(36), primary_key=True, default=_uuid_str)
    simulation_id = db.Column(
        db.String(36),
        db.ForeignKey("simulations.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    total_prompts = db.Column(db.Integer, nullable=False, default=0)
    total_model_runs = db.Column(db.Integer, nullable=False, default=0)
    total_citations = db.Column(db.Integer, nullable=False, default=0)
    total_errors = db.Column(db.Integer, nullable=False, default=0)
    dead_links_count = db.Column(db.Integer, nullable=False, default=0)
    hallucination_count = db.Column(db.Integer, nullable=False, default=0)
    avg_fact_score = db.Column(db.Float)

    top_failure_reasons = db.Column(db.JSON)
    top_mitigations = db.Column(db.JSON)
    competitor_comparison_summary = db.Column(db.Text)

    generated_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    simulation = db.relationship("Simulation", back_populates="report_summary")
