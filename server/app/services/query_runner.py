# app/services/query_runner.py
# -----------------------------------------
# Service: Sends queries to LLM platforms and extracts brand visibility data.
# Called by run_orchestrator batch worker and the query_tester route.
#
# IMPORTS NEEDED:
#   from app.utils.llm_clients import get_chatgpt_response, get_gemini_response
#   from app.utils.llm_clients import get_perplexity_response, get_claude_response
#   from app.models.query import QueryRun, QueryTemplate, LLMPlatform, RunStatus
#   from app.models.company import Company
#   from app.extensions import db
#   import re, time
#   from datetime import datetime, timezone
#
# -----------------------------------------------------------
# FUNCTION: run_template_on_all_platforms(template_id: int) -> list[QueryRun]
# -----------------------------------------------------------
# PURPOSE:
#   Runs one QueryTemplate against all 4 LLM platforms.
#   Creates one QueryRun per platform for an active manual batch.
#
# STEPS:
#   1. Load QueryTemplate and its associated Company from db
#   2. For each LLMPlatform (CHATGPT, GEMINI, PERPLEXITY, CLAUDE):
#         a. Create QueryRun record with status = RUNNING
#         b. Call run_single_query(query_text, platform, company)
#         c. Update QueryRun with results
#         d. Set status = COMPLETED or FAILED
#   3. Return list of completed QueryRun records
#
# -----------------------------------------------------------
# FUNCTION: run_single_query(query_text: str, platform: LLMPlatform, company: Company) -> dict
# -----------------------------------------------------------
# PURPOSE:
#   Sends one query to one LLM platform and returns analysis results.
#   Used directly by query_tester route for live simulation.
#
# STEPS:
#   1. Record start time
#   2. Call the appropriate LLM client based on platform:
#         - CHATGPT    → get_chatgpt_response(query_text)
#         - GEMINI     → get_gemini_response(query_text)
#         - PERPLEXITY → get_perplexity_response(query_text)
#         - CLAUDE     → get_claude_response(query_text)
#   3. Record response_latency_ms = end_time - start_time
#   4. Call extract_brand_mention(raw_response, company) → brand_mentioned, brand_position
#   5. Call extract_citations(raw_response) → list of cited URLs
#   6. Return dict:
#         {
#           "raw_response": str,
#           "brand_mentioned": bool,
#           "brand_position": int | None,
#           "citations_found": list[str],
#           "response_latency_ms": int
#         }
#   7. If LLM API raises exception: return error dict with error_message
#
# -----------------------------------------------------------
# FUNCTION: extract_brand_mention(response_text: str, company: Company) -> tuple[bool, int | None]
# -----------------------------------------------------------
# PURPOSE:
#   Scans AI response text to determine if the brand was mentioned
#   and at what recommendation position.
#
# LOGIC:
#   1. Case-insensitive search for company.name in response_text
#      Also search for common brand name variations (e.g. "Home Depot" vs "HomeDepot")
#   2. If found: brand_mentioned = True
#   3. Detect position:
#         - Find numbered lists (1., 2., 3.) or ordinal markers
#         - If company name appears in/near position marker, record that number
#         - If mentioned but not in a list: position = None (mentioned without ranking)
#   4. Return (brand_mentioned: bool, brand_position: int | None)
#
# -----------------------------------------------------------
# FUNCTION: extract_citations(response_text: str) -> list[str]
# -----------------------------------------------------------
# PURPOSE:
#   Extract URLs and source domain references from AI response text.
#   Some platforms cite sources explicitly; others mention domain names inline.
#
# LOGIC:
#   1. Regex search for http/https URLs in response text
#   2. Regex search for domain-like patterns (e.g. "nerdwallet.com")
#   3. Deduplicate and return list of domain strings (not full URLs)
#      e.g. ["nerdwallet.com", "reddit.com"]
