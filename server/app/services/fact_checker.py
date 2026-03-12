# app/services/fact_checker.py
# -----------------------------------------
# Service: Compares AI response claims against live company pages.
# This is the core of the accuracy layer — determines what the AI got wrong.
#
# IMPORTS NEEDED:
#   import httpx
#   from bs4 import BeautifulSoup
#   from app.utils.llm_clients import get_chatgpt_response   # Used to extract claims
#   from app.models.accuracy import AccuracyCheck, FactualError, ErrorType, ErrorSeverity, RootCause
#   from app.models.query import QueryRun
#   from app.models.company import Company
#   from app.extensions import db
#   from datetime import datetime, timezone
#   import re
#
# -----------------------------------------------------------
# FUNCTION: check_query_run(query_run_id: int) -> AccuracyCheck
# -----------------------------------------------------------
# PURPOSE:
#   Main entry point. Runs the full fact-check pipeline for one QueryRun.
#   Called by daily_queries.py after each query run completes.
#
# STEPS:
#   1. Load QueryRun from db (needs raw_response and company)
#   2. Fetch the relevant live company page:
#         - Determine which page to fetch based on the query type
#           (product page for product queries, policy page for policy queries)
#         - Fetch with httpx, extract clean text via BeautifulSoup
#   3. Call extract_claims(raw_response) → list of factual claims
#   4. Call verify_claims(claims, live_page_text) → list of {claim, correct, ai_value, correct_value}
#   5. Create AccuracyCheck record
#   6. For each wrong claim: create FactualError record
#         - Call root_cause.diagnose(error, page_audit, company) to populate root_cause field
#   7. Update Company.open_error_count
#   8. Return AccuracyCheck
#
# -----------------------------------------------------------
# FUNCTION: extract_claims(response_text: str) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Uses an LLM (GPT-4) to extract all factual claims from an AI response.
#   Returns structured list of claims that can be verified.
#
# APPROACH:
#   Send a meta-prompt to ChatGPT:
#     "Extract all verifiable factual claims from this text as a JSON array.
#      Each claim should have: field_name, stated_value, claim_type."
#   Parse the JSON response.
#   Returns: [{ "field": "APR", "value": "19.99%", "type": "financial" }, ...]
#
# NOTE:
#   This uses an LLM to analyze an LLM's response.
#   Keep the extraction prompt deterministic (low temperature = 0.0).
#
# -----------------------------------------------------------
# FUNCTION: verify_claims(claims: list[dict], live_page_text: str) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Compares each extracted claim against the live page text.
#   Returns verdict for each claim: correct or wrong with details.
#
# LOGIC:
#   For each claim:
#     1. Search live_page_text for the field name (e.g. "APR", "annual fee")
#     2. Extract the corresponding value from the live page using regex patterns
#     3. Compare AI value vs live page value:
#           - Normalize formats (strip %, $, etc. before comparing numbers)
#           - String similarity for non-numeric claims
#     4. Return: { "field": str, "correct": bool, "ai_value": str, "correct_value": str }
#
# -----------------------------------------------------------
# FUNCTION: determine_error_type(field_name: str) -> ErrorType
# -----------------------------------------------------------
# PURPOSE:
#   Maps a field name like "APR" or "price" to an ErrorType enum value.
#   Used when creating FactualError records.
#
# -----------------------------------------------------------
# FUNCTION: determine_severity(error_type: ErrorType, company_industry: str) -> ErrorSeverity
# -----------------------------------------------------------
# PURPOSE:
#   Determines error severity based on error type and company industry.
#   Wrong price → CRITICAL for financial companies, HIGH for retail.
#   Wrong spec → HIGH.
#   Outdated minor fact → MEDIUM/LOW.
