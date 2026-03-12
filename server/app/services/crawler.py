# app/services/crawler.py
# -----------------------------------------
# Service: Website crawler that mimics GPTBot behavior.
# Crawls pages with no JavaScript execution — raw HTTP only.
# This is what AI bots actually see when they index a page.
#
# IMPORTS NEEDED:
#   import httpx                          # Async HTTP client for fast crawling
#   from bs4 import BeautifulSoup         # HTML parsing and text extraction
#   from urllib.parse import urljoin, urlparse
#   from app.models.crawl import CrawlJob, PageAudit, SchemaIssue, CrawlStatus, PageType
#   from app.models.company import Company
#   from app.extensions import db
#   from app.utils.schema_validator import validate_schema
#   import json, re
#   from datetime import datetime, timezone
#
# -----------------------------------------------------------
# FUNCTION: crawl_company(company_id: int) -> CrawlJob
# -----------------------------------------------------------
# PURPOSE:
#   Main entry point for crawling a company's website.
#   Called by manual run flow and /api/crawl/trigger route.
#
# STEPS:
#   1. Load Company from db
#   2. Create CrawlJob record with status = RUNNING
#   3. Fetch sitemap.xml from company.primary_domain + "/sitemap.xml"
#      - If sitemap not found, fall back to crawling from homepage and following links
#   4. Parse sitemap to extract all page URLs
#   5. Check robots.txt for GPTBot disallow rules:
#         - Fetch primary_domain + "/robots.txt"
#         - Look for "User-agent: GPTBot" section
#         - If GPTBot is disallowed: set CrawlJob.bot_blocked = True
#         - Update Company.bot_allowed = False
#   6. For each URL (up to MAX_PAGES = 200):
#         - Call audit_page(url, crawl_job_id) → PageAudit
#   7. Update CrawlJob with final stats: pages_crawled, pages_failed, status = COMPLETED
#   8. Update Company.last_crawled_at = now()
#   9. Return completed CrawlJob
#
# -----------------------------------------------------------
# FUNCTION: audit_page(url: str, crawl_job_id: int, company_id: int) -> PageAudit
# -----------------------------------------------------------
# PURPOSE:
#   Fetches and audits a single page. Creates a PageAudit record.
#
# STEPS:
#   1. Fetch page with httpx (no JS, plain HTTP GET)
#      Set User-Agent to "GPTBot/1.0" to mimic actual bot behavior
#   2. Record http_status and response_time_ms
#   3. Parse with BeautifulSoup:
#         - Extract all visible text (no script/style tags) → bot_readable_text
#         - Count word_count_bot
#   4. Detect page_type from URL pattern and page title:
#         - "/p/" or "/product/" → PRODUCT_PAGE
#         - "/faq" or "/help/" → FAQ_PAGE
#         - "/policy" or "/return" → POLICY_PAGE
#         - Homepage URL → HOMEPAGE
#   5. Extract all JSON-LD script tags:
#         - Parse as JSON, collect @type values → schema_types_found
#         - Call validate_schema() to check for issues
#         - Set has_schema = True if any found
#         - Set has_valid_schema = True only if all pass validation
#   6. For each schema validation error, create a SchemaIssue record
#   7. Calculate content_delta_score:
#         - Compare bot_readable_text length vs estimated JS-rendered length
#         - Higher delta = more JS-hidden content
#         (Note: full human_readable_text requires headless browser — optional)
#   8. Create and return PageAudit record
#
# -----------------------------------------------------------
# FUNCTION: extract_text(html: str) -> str
# -----------------------------------------------------------
# PURPOSE:
#   Extract clean readable text from raw HTML, removing all tags,
#   script blocks, style blocks, nav, header, footer.
#   Returns only the meaningful body content.
#
# -----------------------------------------------------------
# FUNCTION: detect_page_type(url: str, title: str) -> PageType
# -----------------------------------------------------------
# PURPOSE:
#   Classify a URL into a PageType enum value based on URL pattern and page title.
#   Used by audit_page() to set page_type on PageAudit.
#
# -----------------------------------------------------------
# FUNCTION: check_robots_for_gptbot(domain: str) -> bool
# -----------------------------------------------------------
# PURPOSE:
#   Fetch robots.txt and return True if GPTBot is allowed, False if blocked.
#   Checks both "User-agent: GPTBot" and "User-agent: *" sections.
