"""clean auth and simulation schema

Revision ID: 3c1d7a9e4b21
Revises:
Create Date: 2026-03-12 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c1d7a9e4b21"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column(
            "industry_type",
            sa.Enum(
                "RETAIL",
                "FINANCIAL",
                "TECHNOLOGY",
                "MEDIA_SPORTS",
                "GROCERY",
                name="industrytype",
            ),
            nullable=True,
        ),
        sa.Column("primary_domain", sa.String(length=255), nullable=False),
        sa.Column("about_company", sa.Text(), nullable=True),
        sa.Column("approved_email_domain", sa.String(length=255), nullable=True),
        sa.Column("registration_status", sa.String(length=30), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("ai_visibility_score", sa.Float(), nullable=True),
        sa.Column("accuracy_score", sa.Float(), nullable=True),
        sa.Column("top_rec_rate", sa.Float(), nullable=True),
        sa.Column("open_error_count", sa.Integer(), nullable=True),
        sa.Column("bot_allowed", sa.Boolean(), nullable=True),
        sa.Column("last_crawled_at", sa.DateTime(), nullable=True),
        sa.Column("last_queried_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "company_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("enabled_platforms", sa.JSON(), nullable=True),
        sa.Column("priority_pages", sa.JSON(), nullable=True),
        sa.Column("compliance_mode", sa.Boolean(), nullable=True),
        sa.Column("alert_email", sa.String(length=255), nullable=True),
        sa.Column("default_query_count", sa.Integer(), nullable=True),
        sa.Column("max_query_count", sa.Integer(), nullable=True),
        sa.Column("auto_approve_domain_logins", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_id"),
    )

    op.create_table(
        "company_domains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "company_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("full_name", sa.String(length=120), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_company_users_email"), "company_users", ["email"], unique=False
    )

    op.create_table(
        "magic_link_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("requested_from_ip", sa.String(length=100), nullable=True),
        sa.Column("requested_user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["company_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("session_token_hash", sa.String(length=255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_from_ip", sa.String(length=100), nullable=True),
        sa.Column("created_user_agent", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["company_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "simulations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_id", sa.Integer(), nullable=False),
        sa.Column("company_user_id", sa.Integer(), nullable=False),
        sa.Column("time_started", sa.DateTime(), nullable=False),
        sa.Column("time_ended", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("product_specification", sa.Text(), nullable=False),
        sa.Column("n_iteration", sa.Integer(), nullable=False),
        sa.Column("additional_detail", sa.Text(), nullable=True),
        sa.Column("about_company", sa.Text(), nullable=True),
        sa.Column("contact_email", sa.String(length=320), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=True),
        sa.Column("time_created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"]),
        sa.ForeignKeyConstraint(["company_user_id"], ["company_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulations_company_id"), "simulations", ["company_id"], unique=False
    )
    op.create_index(
        op.f("ix_simulations_company_user_id"),
        "simulations",
        ["company_user_id"],
        unique=False,
    )

    op.create_table(
        "prompts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("prompt_order", sa.Integer(), nullable=False),
        sa.Column("time_created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompts_simulation_id"), "prompts", ["simulation_id"], unique=False
    )

    op.create_table(
        "prompt_model_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("prompt_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("success_or_failed", sa.String(length=20), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("mitigation", sa.Text(), nullable=True),
        sa.Column("citations_found_count", sa.Integer(), nullable=False),
        sa.Column("dead_links_count", sa.Integer(), nullable=False),
        sa.Column("fact_score", sa.Float(), nullable=True),
        sa.Column("fact_score_reason", sa.Text(), nullable=True),
        sa.Column("time_created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_prompt_model_runs_prompt_id"),
        "prompt_model_runs",
        ["prompt_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_prompt_model_runs_simulation_id"),
        "prompt_model_runs",
        ["simulation_id"],
        unique=False,
    )

    op.create_table(
        "citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("prompt_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("company_cited", sa.String(length=255), nullable=False),
        sa.Column("website_domain", sa.String(length=255), nullable=False),
        sa.Column("cited_url", sa.String(length=2000), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("time_created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["prompt_model_runs.id"]),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_citations_prompt_id"), "citations", ["prompt_id"], unique=False
    )
    op.create_index(op.f("ix_citations_run_id"), "citations", ["run_id"], unique=False)
    op.create_index(
        op.f("ix_citations_simulation_id"), "citations", ["simulation_id"], unique=False
    )

    op.create_table(
        "errors",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("prompt_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("company_link", sa.String(length=2000), nullable=True),
        sa.Column("error_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("reason_for_failure", sa.Text(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("time_created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["prompt_model_runs.id"]),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_errors_prompt_id"), "errors", ["prompt_id"], unique=False)
    op.create_index(op.f("ix_errors_run_id"), "errors", ["run_id"], unique=False)
    op.create_index(
        op.f("ix_errors_simulation_id"), "errors", ["simulation_id"], unique=False
    )

    op.create_table(
        "fact_checks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("prompt_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("company_link", sa.String(length=2000), nullable=True),
        sa.Column("ai_text_about", sa.Text(), nullable=False),
        sa.Column("fact_score", sa.Float(), nullable=False),
        sa.Column("reason_for_score", sa.Text(), nullable=False),
        sa.Column("mitigation", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=64), nullable=False),
        sa.Column("time_created", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["prompt_id"], ["prompts.id"]),
        sa.ForeignKeyConstraint(["run_id"], ["prompt_model_runs.id"]),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fact_checks_prompt_id"), "fact_checks", ["prompt_id"], unique=False
    )
    op.create_index(
        op.f("ix_fact_checks_run_id"), "fact_checks", ["run_id"], unique=False
    )
    op.create_index(
        op.f("ix_fact_checks_simulation_id"),
        "fact_checks",
        ["simulation_id"],
        unique=False,
    )

    op.create_table(
        "report_summaries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("simulation_id", sa.String(length=36), nullable=False),
        sa.Column("total_prompts", sa.Integer(), nullable=False),
        sa.Column("total_model_runs", sa.Integer(), nullable=False),
        sa.Column("total_citations", sa.Integer(), nullable=False),
        sa.Column("total_errors", sa.Integer(), nullable=False),
        sa.Column("dead_links_count", sa.Integer(), nullable=False),
        sa.Column("hallucination_count", sa.Integer(), nullable=False),
        sa.Column("avg_fact_score", sa.Float(), nullable=True),
        sa.Column("top_failure_reasons", sa.JSON(), nullable=True),
        sa.Column("top_mitigations", sa.JSON(), nullable=True),
        sa.Column("competitor_comparison_summary", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["simulation_id"], ["simulations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_report_summaries_simulation_id"),
        "report_summaries",
        ["simulation_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        op.f("ix_report_summaries_simulation_id"), table_name="report_summaries"
    )
    op.drop_table("report_summaries")

    op.drop_index(op.f("ix_fact_checks_simulation_id"), table_name="fact_checks")
    op.drop_index(op.f("ix_fact_checks_run_id"), table_name="fact_checks")
    op.drop_index(op.f("ix_fact_checks_prompt_id"), table_name="fact_checks")
    op.drop_table("fact_checks")

    op.drop_index(op.f("ix_errors_simulation_id"), table_name="errors")
    op.drop_index(op.f("ix_errors_run_id"), table_name="errors")
    op.drop_index(op.f("ix_errors_prompt_id"), table_name="errors")
    op.drop_table("errors")

    op.drop_index(op.f("ix_citations_simulation_id"), table_name="citations")
    op.drop_index(op.f("ix_citations_run_id"), table_name="citations")
    op.drop_index(op.f("ix_citations_prompt_id"), table_name="citations")
    op.drop_table("citations")

    op.drop_index(
        op.f("ix_prompt_model_runs_simulation_id"), table_name="prompt_model_runs"
    )
    op.drop_index(
        op.f("ix_prompt_model_runs_prompt_id"), table_name="prompt_model_runs"
    )
    op.drop_table("prompt_model_runs")

    op.drop_index(op.f("ix_prompts_simulation_id"), table_name="prompts")
    op.drop_table("prompts")

    op.drop_index(op.f("ix_simulations_company_user_id"), table_name="simulations")
    op.drop_index(op.f("ix_simulations_company_id"), table_name="simulations")
    op.drop_table("simulations")

    op.drop_table("user_sessions")
    op.drop_table("magic_link_tokens")

    op.drop_index(op.f("ix_company_users_email"), table_name="company_users")
    op.drop_table("company_users")

    op.drop_table("company_domains")
    op.drop_table("company_configs")
    op.drop_table("companies")

    sa.Enum(
        "RETAIL",
        "FINANCIAL",
        "TECHNOLOGY",
        "MEDIA_SPORTS",
        "GROCERY",
        name="industrytype",
    ).drop(op.get_bind(), checkfirst=True)
