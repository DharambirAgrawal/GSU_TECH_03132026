# app/services/content_generator.py
# -----------------------------------------
# Service: Generates content fixes using AI based on detected errors and gaps.
# This is the core product differentiator — turning diagnosis into ready-to-ship fixes.
#
# IMPORTS NEEDED:
#   from app.utils.llm_clients import get_chatgpt_response, get_claude_response
#   from app.models.content import ContentFix, FixType, FixStatus
#   from app.models.accuracy import FactualError, RootCause
#   from app.models.crawl import PageAudit, SchemaIssue
#   from app.models.company import Company
#   from app.extensions import db
#   import json
#   from datetime import datetime, timezone
#
# -----------------------------------------------------------
# FUNCTION: generate_fix_for_error(factual_error_id: int) -> ContentFix
# -----------------------------------------------------------
# PURPOSE:
#   Main entry point. Generates the appropriate fix for a FactualError.
#   Chooses fix type based on root_cause of the error.
#
# ROUTING LOGIC based on root_cause:
#   - JS_HIDDEN_CONTENT  → generate_use_case_block() (static content that AI bots can read)
#   - MISSING_SCHEMA     → generate_schema_patch()
#   - INVALID_SCHEMA     → generate_schema_patch()
#   - STALE_CONTENT      → generate_fact_correction()
#   - CONTENT_GAP        → generate_use_case_block() or generate_new_page()
#   - THIRD_PARTY_SOURCE → generate_fact_correction() + note to contact third party
#   - BOT_BLOCKED        → generate_robots_instruction()
#   - TRAINING_DATA      → generate_fact_correction() (best effort)
#
# STEPS:
#   1. Load FactualError with its AccuracyCheck → QueryRun → Company
#   2. Determine fix_type based on root_cause (routing logic above)
#   3. Call appropriate generator function
#   4. Calculate estimated_impact score (0.0–1.0):
#         - CRITICAL severity errors → higher impact
#         - JS_HIDDEN_CONTENT or MISSING_SCHEMA → high impact (many queries affected)
#         - Use occurrence_count to weight impact (recurring errors matter more)
#   5. Create and return ContentFix record
#
# -----------------------------------------------------------
# FUNCTION: generate_schema_patch(error: FactualError, page_audit: PageAudit) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Generates a complete, valid JSON-LD schema markup block correcting
#   the schema issues found on a specific page.
#
# LOGIC:
#   1. Build prompt for Claude (better at code/JSON generation):
#         "Given this product page content: [bot_readable_text]
#          Generate a complete, valid JSON-LD Product schema block with these fields:
#          name, description, offers.price=[correct_value], offers.priceCurrency,
#          brand, sku. Use the correct values from the page content."
#   2. Parse the response to extract the JSON-LD block
#   3. Validate it parses as valid JSON before returning
#   4. Return as formatted JSON string ready to paste into <script type="application/ld+json">
#
# -----------------------------------------------------------
# FUNCTION: generate_use_case_block(error: FactualError, company: Company) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Generates an HTML content block (FAQ-style) that directly answers
#   the query that caused the error. Static HTML so AI bots can read it.
#
# LOGIC:
#   1. Build prompt:
#         "Write an FAQ-style HTML section answering this question: [query_text]
#          Use only these verified facts: [correct_value, source_page_url]
#          The content should be factual, helpful, and formatted in plain HTML.
#          No JavaScript. Include the brand name [company.name] naturally."
#   2. Return the generated HTML block
#
# -----------------------------------------------------------
# FUNCTION: generate_fact_correction(error: FactualError) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Generates corrected copy for an existing page section that
#   contains stale or incorrect information.
#
# LOGIC:
#   1. Fetch the current page content from source_page_url
#   2. Build prompt:
#         "Here is the current page content: [current_text]
#          The AI incorrectly states [ai_stated_value] for [field_name].
#          The correct value is [correct_value].
#          Rewrite the relevant paragraph with the correct information.
#          Keep the same tone and style."
#   3. Return the corrected paragraph(s)
#
# -----------------------------------------------------------
# FUNCTION: generate_robots_instruction(company: Company) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Generates a robots.txt diff showing what to change to allow GPTBot.
#   Not actual content — a technical instruction for the dev team.
#
# LOGIC:
#   1. Fetch current robots.txt
#   2. Find GPTBot disallow rules
#   3. Generate diff showing: remove Disallow for GPTBot, or change to Allow: /
#   4. Return as plain text instruction with before/after comparison
#
# -----------------------------------------------------------
# FUNCTION: estimate_impact(error: FactualError) -> float
# -----------------------------------------------------------
# PURPOSE:
#   Returns a 0.0–1.0 impact score used to prioritize fixes in the Action Center.
#
# SCORING FORMULA:
#   base = severity_weight (critical=1.0, high=0.7, medium=0.4, low=0.2)
#   occurrence_weight = min(error.occurrence_count / 10, 1.0)
#   compliance_bonus = 0.1 if error.compliance_risk else 0.0
#   return min(base * 0.6 + occurrence_weight * 0.3 + compliance_bonus + 0.1, 1.0)
