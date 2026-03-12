# app/routes/visibility.py
# -----------------------------------------
# Blueprint for brand visibility metrics endpoints.
# Registered in create_app() at URL prefix: /api/visibility
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.models.query import QueryRun, QueryTemplate, LLMPlatform
#   from app.models.source import CitationSource, SourceMention
#   from app.extensions import db
#   from sqlalchemy import func, and_
#   import datetime
#
# BLUEPRINT:
#   bp = Blueprint("visibility", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/visibility/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Returns all visibility data for the Visibility tab.
#   LLM mention rates, source domains, winning/losing queries.
#
# QUERY PARAMS:
#   - days: int (default 7) — lookback window for calculations
#   - platform: string (optional) — filter to one LLM platform
#
# LOGIC:
#   1. Look up Company by slug
#   2. Calculate LLM mention rates per platform:
#         - For each LLMPlatform enum value:
#             total = count QueryRun rows for company + platform in last N days
#             mentioned = count rows where brand_mentioned = True
#             rate = mentioned / total * 100
#         - Return dict keyed by platform name
#   3. Get top citation sources:
#         - Query CitationSource ordered by citation_count DESC
#         - Limit to top 20
#         - Include accuracy_concern flag for highlighting risky sources
#   4. Get winning queries (mention_rate = 100%):
#         - Aggregate QueryRun by template_id, filter brand_mentioned = True on all runs
#         - Join QueryTemplate to get query_text and category
#         - Limit to top 10 by consistency
#   5. Get losing queries (expected_brand_mention = True but brand_mentioned = False):
#         - Aggregate QueryRun by template_id, filter brand_mentioned = False
#         - Join QueryTemplate where expected_brand_mention = True
#         - These are critical gaps to fix — sort by occurrence count
#
# RESPONSE SHAPE:
#   {
#     "mention_rates": {
#       "chatgpt": 78.5,
#       "gemini": 65.2,
#       "perplexity": 82.0,
#       "claude": 70.1
#     },
#     "overall_mention_rate": 73.9,
#     "top_sources": [ { ...source.to_dict() } ],
#     "winning_queries": [ { "query_text": "...", "mention_rate": 100.0 } ],
#     "losing_queries": [ { "query_text": "...", "mention_rate": 0.0, "expected": true } ]
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/visibility/<company_slug>/sources
# -----------------------------------------------------------
# PURPOSE:
#   Returns the full list of citation sources with filtering.
#   Powers the source domain table on the Visibility tab.
#
# QUERY PARAMS:
#   - source_type: string (optional) filter by SourceType
#   - accuracy_concern: bool (optional) filter to risky sources only
#   - sort: "citation_count" | "negative_count" (default citation_count)
#
# LOGIC:
#   1. Look up Company
#   2. Build SQLAlchemy query with optional filters from query params
#   3. Order by chosen sort field DESC
#   4. Return paginated list of sources with mention count history
#
# -----------------------------------------------------------
# ROUTE 3: GET /api/visibility/<company_slug>/platforms
# -----------------------------------------------------------
# PURPOSE:
#   Returns per-platform breakdown over time.
#   Powers the line chart showing each platform's mention rate week by week.
#
# LOGIC:
#   1. Group QueryRun by (platform, week) for last 8 weeks
#   2. Calculate mention rate per group
#   3. Return array of { week, chatgpt, gemini, perplexity, claude } objects
#
# ERROR HANDLING (all routes):
#   - 404 if company not found
#   - 500 on DB errors
