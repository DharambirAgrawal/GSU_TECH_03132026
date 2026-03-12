# app/routes/crawl.py
# -----------------------------------------
# Blueprint for website crawl and readability audit endpoints.
# Registered in create_app() at URL prefix: /api/crawl
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.models.crawl import CrawlJob, PageAudit, SchemaIssue, CrawlStatus
#   from app.extensions import db
#   from app.services.run_orchestrator import enqueue_crawl_task_for_company
#
# BLUEPRINT:
#   bp = Blueprint("crawl", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/crawl/<company_slug>/latest
# -----------------------------------------------------------
# PURPOSE:
#   Returns the results of the most recent completed CrawlJob for a company.
#   Powers the Readability Audit view on the Accuracy tab.
#
# LOGIC:
#   1. Look up Company by slug
#   2. Get most recent CrawlJob where status = COMPLETED
#   3. Return CrawlJob summary:
#         - pages_crawled, pages_failed, bot_blocked, completed_at
#   4. Return aggregated PageAudit stats:
#         - total pages
#         - pages with content_delta_score > 0.5 (high JS gap)
#         - pages with no valid schema (has_valid_schema = False)
#         - pages with bot http_status != 200 (blocked or broken)
#         - average word_count_bot across all pages
#   5. Return top 20 problem pages (highest content_delta_score)
#   6. Return SchemaIssue summary grouped by issue_type
#
# RESPONSE SHAPE:
#   {
#     "crawl_job": { ...crawl_job.to_dict() },
#     "stats": {
#       "total_pages": 145,
#       "high_js_gap_pages": 23,
#       "no_schema_pages": 67,
#       "blocked_pages": 4,
#       "avg_bot_word_count": 312
#     },
#     "problem_pages": [ { ...page_audit.to_dict() } ],
#     "schema_issue_summary": { "missing_field": 42, "invalid_value": 15 }
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/crawl/<company_slug>/history
# -----------------------------------------------------------
# PURPOSE:
#   Returns the list of all CrawlJobs for a company (crawl history).
#   Shows how crawl coverage and quality has changed over time.
#
# LOGIC:
#   1. Look up Company
#   2. Return all CrawlJobs ordered by created_at DESC, limit 20
#   3. Each entry includes: status, pages_crawled, pages_failed, completed_at
#
# -----------------------------------------------------------
# ROUTE 3: GET /api/crawl/page/<page_audit_id>
# -----------------------------------------------------------
# PURPOSE:
#   Returns the full details for a single PageAudit.
#   Includes bot_readable_text, human_readable_text, and all SchemaIssues.
#   Used when a user drills into a specific page from the audit list.
#
# LOGIC:
#   1. Look up PageAudit by id
#   2. Return full audit dict including the full text fields
#   3. Include all linked SchemaIssue records
#
# -----------------------------------------------------------
# ROUTE 4: POST /api/crawl/<company_slug>/trigger
# -----------------------------------------------------------
# PURPOSE:
#   Manually trigger an immediate crawl for a company.
#   Kicks off an asynchronous crawl task for this company only.
#
# LOGIC:
#   1. Look up Company by slug
#   2. Check if a crawl is already RUNNING for this company (409 if so)
#   3. Create a new CrawlJob record with status = PENDING
#   4. Call trigger_crawl_for_company(company_id) in a background thread
#   5. Return { "crawl_job_id": id, "status": "pending" } immediately
#      (crawl runs async — client can poll /api/crawl/<slug>/latest to see progress)
#
# ERROR HANDLING:
#   - 404 if company not found
#   - 409 if crawl already running
#   - 500 on trigger failure
