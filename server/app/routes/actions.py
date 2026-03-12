# app/routes/actions.py
# -----------------------------------------
# Blueprint for the Action Center — content fix queue management.
# Registered in create_app() at URL prefix: /api/actions
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.models.content import ContentFix, FixStatus, PublishedFix
#   from app.extensions import db
#   from datetime import datetime, timezone
#
# BLUEPRINT:
#   bp = Blueprint("actions", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/actions/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Returns the Action Center queue — all pending ContentFix records
#   ordered by estimated impact (highest impact first).
#   This is the prioritized "what to do next" list for the content team.
#
# QUERY PARAMS:
#   - status: string (optional, default "generated,approved") — filter by FixStatus
#   - fix_type: string (optional) — filter by FixType
#   - effort: string (optional) — "low", "medium", "high" effort filter
#
# LOGIC:
#   1. Look up Company by slug
#   2. Query ContentFix for this company with status IN [GENERATED, APPROVED]
#      (published, rejected, superseded are not in the action queue)
#   3. Apply optional filters from query params
#   4. Order by estimated_impact DESC, then effort_level ASC (high impact, low effort first)
#   5. For each fix, include the linked FactualError summary if it exists
#   6. Return list with count summary (total, by_fix_type, by_effort)
#
# RESPONSE SHAPE:
#   {
#     "total": 14,
#     "summary": { "low_effort": 5, "medium_effort": 7, "high_effort": 2 },
#     "fixes": [
#       {
#         "id": 42,
#         "fix_type": "schema_patch",
#         "title": "Fix Product schema on cordless drill page",
#         "target_page_url": "https://...",
#         "estimated_impact": 0.87,
#         "effort_level": "low",
#         "status": "generated",
#         "linked_error": { ...error summary... }
#       }
#     ]
#   }
#
# -----------------------------------------------------------
# ROUTE 2: PATCH /api/actions/<fix_id>/status
# -----------------------------------------------------------
# PURPOSE:
#   Update the status of a ContentFix.
#   Used for the approve / reject / mark-published workflow buttons in the UI.
#
# REQUEST BODY:
#   {
#     "status": "approved" | "rejected" | "published",
#     "reviewed_by": "user@company.com",
#     "review_notes": "Approved — sending to dev team"
#   }
#
# LOGIC:
#   1. Look up ContentFix by id
#   2. Validate that status transition is allowed:
#         GENERATED → APPROVED or REJECTED
#         APPROVED  → PUBLISHED or REJECTED
#   3. Update status, reviewed_by, and review_notes
#   4. If new status = PUBLISHED:
#         - Set published_at = now()
#         - Create a PublishedFix record (snapshot of published content)
#         - Store before_score = Company.accuracy_score at this moment
#   5. Commit and return updated fix dict
#
# -----------------------------------------------------------
# ROUTE 3: GET /api/actions/<company_slug>/published
# -----------------------------------------------------------
# PURPOSE:
#   Returns history of all published fixes with impact scores.
#   Powers the "Proven Impact" section showing ROI of Vigil fixes.
#
# LOGIC:
#   1. Query PublishedFix for company ordered by published_at DESC
#   2. Include score_delta (after_score - before_score) where measured
#   3. Return list with total measured improvements and average score delta
#
# -----------------------------------------------------------
# ROUTE 4: GET /api/actions/<fix_id>
# -----------------------------------------------------------
# PURPOSE:
#   Returns the full detail view for a single ContentFix.
#   Includes the full generated_content (which can be large HTML/JSON-LD).
#
# LOGIC:
#   1. Look up ContentFix by id
#   2. Return complete fix dict including generated_content
#   3. Include linked FactualError in full detail
#
# ERROR HANDLING:
#   - 404 if company or fix not found
#   - 400 if invalid status transition
#   - 500 on DB errors
