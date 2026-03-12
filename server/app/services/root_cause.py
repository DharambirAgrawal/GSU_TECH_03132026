# app/services/root_cause.py
# -----------------------------------------
# Service: Diagnoses WHY an AI error occurred and generates plain-English explanation.
# Used by fact_checker.py after errors are detected to populate root_cause fields.
#
# IMPORTS NEEDED:
#   from app.models.accuracy import FactualError, RootCause
#   from app.models.crawl import PageAudit, CrawlJob
#   from app.models.company import Company
#   from app.models.source import CitationSource
#   from app.extensions import db
#   from sqlalchemy import func
#
# -----------------------------------------------------------
# FUNCTION: diagnose(error: FactualError, company: Company) -> tuple[RootCause, str, str | None]
# -----------------------------------------------------------
# PURPOSE:
#   Main entry point. Determines the most likely root cause for a FactualError.
#   Returns (root_cause, root_cause_detail, third_party_source).
#
# DIAGNOSIS DECISION TREE:
#   1. BOT_BLOCKED check:
#         - If Company.bot_allowed = False → RootCause.BOT_BLOCKED
#         - Detail: "GPTBot is blocked in your robots.txt file. AI cannot read any pages."
#
#   2. JS_HIDDEN_CONTENT check:
#         - Look up the most recent PageAudit for the source_page_url
#         - If page_audit.content_delta_score > 0.5 → RootCause.JS_HIDDEN_CONTENT
#         - Detail: "The [field_name] on [url] loads via JavaScript.
#                    AI bots cannot execute JS, so they see an older/empty value.
#                    The content visible to bots has [word_count_bot] words vs
#                    [word_count_human] words in a real browser."
#
#   3. INVALID_SCHEMA / MISSING_SCHEMA check:
#         - Look up PageAudit for source_page_url
#         - If not has_schema → RootCause.MISSING_SCHEMA
#         - If has_schema but not has_valid_schema → RootCause.INVALID_SCHEMA
#         - Detail: "The page has no structured data (schema.org markup).
#                    AI uses schema to reliably extract [field_name] values."
#
#   4. THIRD_PARTY_SOURCE check:
#         - Look through citations_found in the QueryRun that triggered this error
#         - If a non-company domain with accuracy_concern = True is present
#         - → RootCause.THIRD_PARTY_SOURCE
#         - third_party_source = the offending domain
#         - Detail: "[domain] published an article that still shows [ai_stated_value]
#                    for [field_name] and currently ranks above your own page for this query."
#
#   5. STALE_CONTENT check:
#         - If the page is readable (no JS gap, schema ok) but value is wrong
#         - Page content itself has wrong/outdated information
#         - → RootCause.STALE_CONTENT
#         - Detail: "Your page at [url] still shows [ai_stated_value].
#                    The content needs to be updated to reflect the correct value."
#
#   6. CONTENT_GAP check:
#         - If source_page_url is None (no page found covering this query)
#         - → RootCause.CONTENT_GAP
#         - Detail: "You don't have any page that directly answers this query.
#                    AI is pulling information from other sources by default."
#
#   7. Default fallback:
#         - → RootCause.TRAINING_DATA
#         - Detail: "The error appears to come from the AI's training data.
#                    Your page is readable and accurate, but the AI is citing old information."
#
# -----------------------------------------------------------
# FUNCTION: generate_content_gap_note(our_rank: int | None, their_rank: int, company: Company, competitor_name: str, cited_urls: list[str]) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Generates the content_gap_notes field for a CompetitorRanking.
#   Plain English explanation of why the competitor ranked higher.
#
# LOGIC:
#   1. If our_rank is None: "Home Depot was not mentioned. Lowe's was ranked #1."
#   2. If their_rank < our_rank:
#         "Lowe's ranked #{their_rank} vs Home Depot's #{our_rank}.
#          Lowe's was cited from: [cited_urls]. Consider creating content
#          similar to these pages to close the gap."
#   3. Include specific recommendation if content gap is clear from citations
