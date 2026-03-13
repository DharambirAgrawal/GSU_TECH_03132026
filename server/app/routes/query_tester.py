# app/routes/query_tester.py
# -----------------------------------------
# Blueprint for low-level query simulation endpoints.
from flask import Blueprint

bp = Blueprint("query_tester", __name__)

# This module remains useful for direct ad-hoc tests, while the
# primary frontend flow now uses /api/runs for async batch execution
# and history tracking.
# Registered in create_app() at URL prefix: /api/query
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.services.query_runner import run_single_query
#   from app.services.fact_checker import check_response_accuracy
#   from app.models.query import LLMPlatform
#   from pydantic import BaseModel, ValidationError
#
# BLUEPRINT:
#   bp = Blueprint("query_tester", __name__)
#
# -----------------------------------------------------------
# PYDANTIC VALIDATION MODEL (define at top of file):
#
#   class SimulateQueryRequest(BaseModel):
#       company_slug: str
#       query_text: str
#       platforms: list[str] = ["chatgpt", "gemini", "perplexity", "claude"]
#       # Optional: which platforms to run against. Default: all 4.
#       run_fact_check: bool = True
#       # If False, skip fact-checking step for faster response
#
# -----------------------------------------------------------
# ROUTE 1: POST /api/query/simulate
# -----------------------------------------------------------
# PURPOSE:
#   Runs a live ad-hoc query against one or more LLM platforms
#   and returns the responses with brand mention analysis and
#   optional fact-checking.
#
# IMPORTANT:
#   This endpoint is synchronous and best for lightweight testing.
#   For production workflow (user chooses N prompts, edits them,
#   starts run without waiting, then checks history), use /api/runs.
#
# REQUEST BODY:
#   {
#     "company_slug": "home_depot",
#     "query_text": "What is the best cordless drill under $200?",
#     "platforms": ["chatgpt", "gemini"],
#     "run_fact_check": true
#   }
#
# LOGIC:
#   1. Parse and validate request body using SimulateQueryRequest Pydantic model
#      Return 400 with validation errors if invalid
#   2. Look up Company by slug (404 if not found)
#   3. For each platform in the request:
#         a. Call query_runner.run_single_query(query_text, platform) → raw_response
#         b. Analyze raw_response for brand mention:
#               - Check if company.name appears in response (case-insensitive)
#               - Detect brand position (which recommendation number)
#               - Extract cited URLs from response text
#         c. If run_fact_check = True:
#               - Call fact_checker.check_response_accuracy(raw_response, company)
#               - Returns list of claims_checked, claims_correct, factual_errors found
#   4. Return all platform results combined
#
# RESPONSE SHAPE:
#   {
#     "query_text": "What is the best cordless drill under $200?",
#     "company": "Home Depot",
#     "results": [
#       {
#         "platform": "chatgpt",
#         "raw_response": "For cordless drills under $200...",
#         "brand_mentioned": true,
#         "brand_position": 2,
#         "citations_found": ["homedepot.com/...", "nerdwallet.com/..."],
#         "response_latency_ms": 1842,
#         "fact_check": {
#           "claims_checked": 5,
#           "claims_correct": 4,
#           "claims_wrong": 1,
#           "errors": [
#             {
#               "field": "price",
#               "ai_said": "$149",
#               "correct": "$169",
#               "severity": "high"
#             }
#           ]
#         }
#       },
#       { "platform": "gemini", ... }
#     ],
#     "summary": {
#       "platforms_ran": 2,
#       "mentioned_on": 1,
#       "overall_mention_rate": 50.0,
#       "total_errors_found": 1
#     }
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/query/<company_slug>/templates
# -----------------------------------------------------------
# PURPOSE:
#   Returns all QueryTemplates for a company so the UI can
#   generate company-aware prompt sets before creating a run draft.
#
# LOGIC:
#   1. Look up Company
#   2. Return all active QueryTemplates grouped by category
#      Each template includes id, query_text, category, expected_brand_mention
#
# -----------------------------------------------------------
# ROUTE 3: POST /api/query/<company_slug>/templates
# -----------------------------------------------------------
# PURPOSE:
#   Add a new QueryTemplate for a company.
#   Used to curate the query library that powers future run suggestions.
#
# REQUEST BODY:
#   {
#     "query_text": "What credit card has the best travel rewards?",
#     "category": "product_recommendation",
#     "priority": 3,
#     "expected_brand_mention": true
#   }
#
# LOGIC:
#   1. Look up Company
#   2. Validate request body (all required fields present)
#   3. Create QueryTemplate, commit, return it
#
# ERROR HANDLING:
#   - 400 if request body invalid or required fields missing
#   - 404 if company not found
#   - 500 if LLM API call fails during simulation
#     (return partial results for platforms that succeeded)
