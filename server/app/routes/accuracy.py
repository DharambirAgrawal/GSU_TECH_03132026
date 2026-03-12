# app/routes/accuracy.py
# -----------------------------------------
# Blueprint for accuracy and fact-checking endpoints.
# Registered in create_app() at URL prefix: /api/accuracy
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.models.accuracy import AccuracyCheck, FactualError, ErrorType, ErrorSeverity, RootCause
#   from app.models.query import QueryRun, LLMPlatform
#   from app.models.crawl import CrawlJob, PageAudit, SchemaIssue
#   from app.extensions import db
#   from sqlalchemy import func, and_
#
# BLUEPRINT:
#   bp = Blueprint("accuracy", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/accuracy/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Returns accuracy breakdown data for the Accuracy tab.
#   Broken down by error type category and by LLM platform.
#
# LOGIC:
#   1. Look up Company by slug
#   2. Accuracy by category:
#         - Group FactualError by error_type
#         - Count occurrences and distinct query runs affected per type
#         - Return as dict: { error_type: { count, affected_runs, severity_breakdown } }
#   3. Accuracy by platform:
#         - Join AccuracyCheck → QueryRun → filter by company
#         - Group by QueryRun.platform
#         - Calculate: (accurate_runs / total_runs) * 100 per platform
#   4. Accuracy trend (last 8 weeks):
#         - Group AccuracyCheck by week, compute accuracy rate per week
#         - Allows charting accuracy over time
#
# RESPONSE SHAPE:
#   {
#     "by_category": {
#       "wrong_price": { "count": 12, "severity": "critical" },
#       "wrong_policy": { "count": 3, "severity": "high" }
#     },
#     "by_platform": {
#       "chatgpt": 88.0,
#       "gemini": 91.0,
#       "perplexity": 85.5,
#       "claude": 93.2
#     },
#     "overall_accuracy": 89.4,
#     "weekly_trend": [
#       { "week": "2026-01-05", "accuracy": 87.0 }, ...
#     ]
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/accuracy/<company_slug>/errors
# -----------------------------------------------------------
# PURPOSE:
#   Returns the full Error Log — all FactualErrors with root cause
#   and linked ContentFix details.
#
# QUERY PARAMS:
#   - severity: string (optional) — filter by ErrorSeverity
#   - error_type: string (optional) — filter by ErrorType
#   - is_resolved: bool (optional, default False) — show resolved or open
#   - page: int (default 1) — pagination
#   - per_page: int (default 25) — results per page
#
# LOGIC:
#   1. Build filter query against FactualError for this company
#   2. Apply query param filters
#   3. Order by severity DESC, then by occurrence_count DESC (worst first)
#   4. Paginate results
#   5. For each error, include the linked ContentFix summary if it exists
#
# -----------------------------------------------------------
# ROUTE 3: GET /api/accuracy/<company_slug>/readability
# -----------------------------------------------------------
# PURPOSE:
#   Returns the AI readability audit from the latest CrawlJob.
#   Powers the Readability Audit section on the Accuracy tab.
#
# LOGIC:
#   1. Get most recent completed CrawlJob for this company
#   2. Return aggregated stats:
#         - total pages audited
#         - pages with content delta score > 0.5 (high JS gap)
#         - pages with no valid schema
#         - pages where bot_readable_text word count < 100 (nearly empty for AI)
#   3. Return list of worst-offending pages (high delta score or no schema)
#         sorted by content_delta_score DESC, limit 20
#   4. Return total SchemaIssue count grouped by issue type
#
# -----------------------------------------------------------
# ROUTE 4: PATCH /api/accuracy/errors/<error_id>/resolve
# -----------------------------------------------------------
# PURPOSE:
#   Mark a FactualError as resolved.
#   Triggers recalculation of Company.accuracy_score and open_error_count.
#
# REQUEST BODY:
#   { "resolution_note": "Fix published on 2026-03-12" }
#
# LOGIC:
#   1. Look up FactualError by id
#   2. Set is_resolved = True, resolved_at = now(), resolution_note from body
#   3. Recalculate Company.open_error_count (count remaining unresolved errors)
#   4. Commit and return updated error dict
#
# ERROR HANDLING:
#   - 404 if company or error not found
#   - 400 if invalid filter params
#   - 500 on DB errors
