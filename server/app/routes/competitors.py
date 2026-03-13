# app/routes/competitors.py
# -----------------------------------------
# Blueprint for competitor tracking and ranking endpoints.
from flask import Blueprint

bp = Blueprint("competitors", __name__)

# Registered in create_app() at URL prefix: /api/competitors
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.models.competitor import Competitor, CompetitorRanking
#   from app.models.query import QueryRun, QueryTemplate
#   from app.extensions import db
#   from sqlalchemy import func, and_
#
# BLUEPRINT:
#   bp = Blueprint("competitors", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/competitors/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Returns the full competitor ranking analysis for the Competitors tab.
#   Head-to-head AI positioning and content gap analysis.
#
# QUERY PARAMS:
#   - days: int (default 7) — lookback window
#   - category: string (optional) — filter by QueryCategory
#
# LOGIC:
#   1. Look up Company by slug
#   2. Get all active Competitors for this company
#   3. For each competitor, aggregate CompetitorRanking rows:
#         - total_queries: count of distinct query runs tracked
#         - our_mention_rate: % of runs where our company was mentioned
#         - their_mention_rate: % of runs where competitor was mentioned
#         - our_avg_position: average our_position when mentioned
#         - their_avg_position: average their_position when mentioned
#         - we_win_count: runs where our_position < their_position (both mentioned)
#         - they_win_count: runs where their_position < our_position (both mentioned)
#   4. Sort competitors by they_win_count DESC (biggest threats first)
#   5. Return ranking table
#
# RESPONSE SHAPE:
#   {
#     "competitors": [
#       {
#         "name": "Lowe's",
#         "our_mention_rate": 72.0,
#         "their_mention_rate": 68.0,
#         "our_avg_position": 1.8,
#         "their_avg_position": 2.1,
#         "we_win_count": 45,
#         "they_win_count": 28
#       }
#     ]
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/competitors/<company_slug>/content-gaps
# -----------------------------------------------------------
# PURPOSE:
#   Returns content gap analysis — where competitors outrank us
#   and what content we're missing.
#   Powers the content gap section of the Competitors tab.
#
# LOGIC:
#   1. Query CompetitorRanking rows where their_position < our_position
#      (or our_position is null = we weren't mentioned)
#   2. Group by competitor_id
#   3. For each competitor and each query where they outranked us:
#         - Include content_gap_notes (from root_cause.py analysis)
#         - Include they_were_cited_from (source domains they have that we don't)
#         - Deduplicate and rank by frequency of the gap appearing
#   4. Return top 10 content gaps per competitor
#
# -----------------------------------------------------------
# ROUTE 3: POST /api/competitors/<company_slug>/add
# -----------------------------------------------------------
# PURPOSE:
#   Add a new competitor to track for this company.
#
# REQUEST BODY:
#   { "name": "Lowe's", "primary_domain": "https://www.lowes.com" }
#
# LOGIC:
#   1. Look up Company by slug
#   2. Check if competitor with same domain already exists for this company (409 if so)
#   3. Create new Competitor record with auto-generated slug
#   4. Return created competitor dict
#
# -----------------------------------------------------------
# ROUTE 4: DELETE /api/competitors/<competitor_id>
# -----------------------------------------------------------
# PURPOSE:
#   Remove a competitor from tracking (soft delete — set is_active = False).
#
# LOGIC:
#   1. Look up Competitor by id
#   2. Set is_active = False (preserve historical ranking data)
#   3. Return success confirmation
#
# ERROR HANDLING:
#   - 404 if company or competitor not found
#   - 409 if adding duplicate competitor domain
#   - 500 on DB errors
