# app/routes/dashboard.py
# -----------------------------------------
# Blueprint for the main dashboard overview endpoints.
# Registered in create_app() at URL prefix: /api/dashboard
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify
#   from app.models.company import Company
#   from app.models.query import QueryRun
#   from sqlalchemy import func
#   import datetime
#
# BLUEPRINT:
#   bp = Blueprint("dashboard", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/dashboard/overview/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Returns all data needed to render the dashboard Overview tab.
#   Designed to be a single endpoint so the frontend makes one request
#   and gets everything needed to paint the full page.
#
# LOGIC:
#   1. Look up Company by slug (404 if not found)
#   2. Return cached scores directly from Company model fields:
#         - ai_visibility_score
#         - accuracy_score
#         - top_rec_rate
#         - open_error_count
#         - bot_allowed (show critical banner if False)
#   3. Calculate zero-click estimate:
#         - Count total QueryRun rows for this company in last 7 days
#         - Divide by estimated UTM-tracked visits (placeholder or from config)
#         - Return ratio as "zero_click_estimate" percent
#   4. Fetch 8-week trend data:
#         - Query Company score history (if ScoreSnapshot model added)
#         - For now: group QueryRun rows by week, compute weekly mention rate
#         - Return array of {week, visibility_score, accuracy_score} for 8 weeks
#   5. Return summary of last query run and last crawl timestamps
#
# RESPONSE SHAPE:
#   {
#     "company": { ...company.to_dict() },
#     "scores": {
#       "ai_visibility": 72.3,
#       "accuracy": 88.1,
#       "top_rec_rate": 34.5,
#       "open_errors": 7,
#       "bot_allowed": true
#     },
#     "zero_click_estimate": 18.2,
#     "trends": [
#       { "week": "2026-01-05", "visibility": 68.0, "accuracy": 85.0 },
#       ...
#     ],
#     "last_queried_at": "2026-03-12T10:00:00",
#     "last_crawled_at": "2026-03-10T02:00:00"
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/dashboard/scores/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Lightweight endpoint that returns ONLY the 4 headline scores.
#   Used for polling/refreshing scores without re-fetching all trend data.
#
# LOGIC:
#   1. Look up Company by slug
#   2. Return only the 4 cached score fields + open_error_count
#
# RESPONSE SHAPE:
#   {
#     "ai_visibility_score": 72.3,
#     "accuracy_score": 88.1,
#     "top_rec_rate": 34.5,
#     "open_error_count": 7
#   }
#
# ERROR HANDLING (both routes):
#   - 404 if company slug not found
#   - 500 with error message if DB query fails
