# app/utils/schema_validator.py
# -----------------------------------------
# Validates JSON-LD schema markup found on crawled pages.
# Called by crawler.py for each page that has schema markup.
# Returns a list of SchemaIssue data dicts for each problem found.
#
# IMPORTS NEEDED:
#   from app.models.crawl import SchemaIssueType
#   import json
#   from typing import Any
#
# SCHEMA REQUIREMENTS BY TYPE:
#   These are the minimum required fields AI platforms need to reliably
#   extract information from schema markup:
#
#   Product schema required fields:
#     - @type: "Product"
#     - name: string
#     - description: string
#     - offers: { @type: "Offer", price: number, priceCurrency: string, availability }
#     - brand: { @type: "Brand", name: string }
#
#   FAQPage schema required fields:
#     - @type: "FAQPage"
#     - mainEntity: list of { @type: "Question", name: string, acceptedAnswer: { text: string } }
#
#   Article schema required fields:
#     - @type: "Article"
#     - headline: string
#     - datePublished: ISO date string
#     - author: { @type: "Person" or "Organization", name: string }
#
#   BreadcrumbList schema required fields:
#     - @type: "BreadcrumbList"
#     - itemListElement: list
#
# -----------------------------------------------------------
# FUNCTION: validate_schema(schema_blocks: list[dict]) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Main entry point. Validates a list of JSON-LD schema objects extracted
#   from a page. Returns a list of issue dicts for creating SchemaIssue records.
#
# STEPS:
#   1. For each schema block in schema_blocks:
#         a. Check @type is present → MISSING_TYPE issue if not
#         b. Route to the appropriate type-specific validator:
#               "Product"       → validate_product_schema(block)
#               "FAQPage"       → validate_faq_schema(block)
#               "Article"       → validate_article_schema(block)
#               "BreadcrumbList"→ validate_breadcrumb_schema(block)
#               Any other type  → basic validation (just check @context)
#   2. Collect all issues from all blocks
#   3. Return list of dicts:
#         [{
#           "issue_type": SchemaIssueType.MISSING_FIELD.value,
#           "field_path": "offers.price",
#           "current_value": None,
#           "expected_value": "A valid number (e.g. 29.99)",
#           "description": "Product schema is missing the offers.price field.",
#           "auto_fixable": True
#         }]
#
# -----------------------------------------------------------
# FUNCTION: validate_product_schema(schema: dict) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Validates a Product schema block against required fields.
#
# CHECKS:
#   - "name" field present and non-empty
#   - "description" field present
#   - "offers" object present:
#       - "price" is a number (not a string like "$29.99")
#       - "priceCurrency" is a valid 3-letter currency code
#       - "availability" is a valid schema.org/InStock or similar URL
#   - "brand" object present with "name"
#   - "sku" present (optional but recommended)
#
# RETURNS list of issue dicts (empty list if all valid)
#
# -----------------------------------------------------------
# FUNCTION: validate_faq_schema(schema: dict) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Validates a FAQPage schema block.
#
# CHECKS:
#   - "mainEntity" is present and is a non-empty list
#   - Each item in mainEntity has:
#       - @type = "Question"
#       - "name" (the question text)
#       - "acceptedAnswer" with "text" (the answer text)
#
# -----------------------------------------------------------
# FUNCTION: validate_article_schema(schema: dict) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Validates an Article/BlogPosting schema block.
#
# CHECKS:
#   - "headline" present and under 110 characters (Google limit)
#   - "datePublished" present and valid ISO 8601 format
#   - "dateModified" present (optional but recommended)
#   - "author" present with nested "name"
#
# -----------------------------------------------------------
# FUNCTION: check_price_freshness(schema: dict, page_text: str) -> dict | None
# -----------------------------------------------------------
# PURPOSE:
#   Compares the price in a Product schema against the price visible
#   in the page's plain text.
#   If they differ, returns an OUTDATED_PRICE issue.
#
# LOGIC:
#   1. Extract schema price value from offers.price
#   2. Search page_text for price patterns (regex: \$[\d,]+\.?\d{0,2})
#   3. Compare: if schema price != page price → return OUTDATED_PRICE issue
#      Include current_value = schema price, expected_value = page price
