# app/jobs/daily_queries.py
# -----------------------------------------
# Background job: Runs all active query templates against all LLM platforms.
# Scheduled to run every 24 hours by APScheduler (registered in create_app).
#
# IMPORTS NEEDED:
#   from app import create_app                        # Need app context for db queries
#   from app.extensions import db
#   from app.models.company import Company
#   from app.models.query import QueryTemplate
#   from app.services.query_runner import run_template_on_all_platforms
#   from app.services.fact_checker import check_query_run
#   from app.services.root_cause import diagnose
#   from app.services.content_generator import generate_fix_for_error
#   from app.services.scoring import update_all_scores
#   from app.models.ethics import EthicsFlag, EthicsCategory, EthicsSeverity, AlertStatus
#   import logging
#   from datetime import datetime, timezone
#
# -----------------------------------------------------------
# FUNCTION: run_daily_queries()
# -----------------------------------------------------------
# PURPOSE:
#   Main job function registered with APScheduler.
#   Processes every company, every active query template, every platform.
#
# EXECUTION PIPELINE:
#   1. Create Flask app context (required for db access in background thread)
#      with app.app_context():
#
#   2. Get all companies from db (loop each company)
#
#   3. For each company:
#      a. Get all active QueryTemplates ordered by priority ASC (highest priority first)
#
#      b. For each template:
#            i.  Call run_template_on_all_platforms(template.id) → list[QueryRun]
#            ii. For each completed QueryRun:
#                - Call check_query_run(query_run.id) → AccuracyCheck
#                - For each FactualError in the AccuracyCheck:
#                    * Call diagnose(error, company) → populate root_cause
#                    * If error.compliance_risk = True: create EthicsFlag
#                    * If error.severity = CRITICAL: trigger compliance alert
#                    * Call generate_fix_for_error(error.id) → ContentFix
#
#      c. After all templates processed for this company:
#            - Call update_all_scores(company.id) → recalculate cached scores
#            - Update Company.last_queried_at = now()
#            - Commit all changes
#
#   4. Log completion with summary stats:
#      "Daily queries complete: X companies, Y templates, Z runs, W errors found"
#
# ERROR HANDLING:
#   - Wrap each template in try/except so one failure doesn't stop all others
#   - Log exceptions with company_id and template_id for debugging
#   - If a company's entire batch fails, log but continue to next company
#
# RATE LIMITING:
#   - Add configurable delay between LLM API calls (default: 1 second sleep)
#   - If an LLM client raises RateLimitError: back off and retry after 60 seconds
#   - Maximum 3 retries per template-platform combination
#
# -----------------------------------------------------------
# FUNCTION: run_daily_queries_for_company(company_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Runs the daily query pipeline for just one company.
#   Used for manual re-runs without waiting for the full batch.
#   Callable from the Flask shell or admin endpoints.
#
# SAME LOGIC AS run_daily_queries() but scoped to one company.
