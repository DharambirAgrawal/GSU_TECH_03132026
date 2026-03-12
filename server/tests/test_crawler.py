# tests/test_crawler.py
# -----------------------------------------
# Unit tests for the website crawler service.
# Tests page fetching, text extraction, schema detection, and robots.txt parsing.
# All HTTP requests must be mocked — tests should not hit real websites.
#
# IMPORTS NEEDED:
#   import pytest
#   from unittest.mock import patch, MagicMock, AsyncMock
#   from app import create_app
#   from app.extensions import db
#   from app.models.company import Company, IndustryType
#   from app.models.crawl import CrawlJob, PageAudit, SchemaIssue, CrawlStatus
#   from app.services.crawler import (
#       crawl_company,
#       audit_page,
#       extract_text,
#       detect_page_type,
#       check_robots_for_gptbot
#   )
#
# -----------------------------------------------------------
# TEST CONSTANTS (sample HTML for mocking responses):
#
#   SAMPLE_PRODUCT_HTML — HTML with a Product JSON-LD block, prices, nav
#   SAMPLE_ROBOTS_ALLOW — robots.txt that allows GPTBot
#   SAMPLE_ROBOTS_BLOCK — robots.txt that blocks GPTBot
#   SAMPLE_ROBOTS_PARTIAL — robots.txt with no GPTBot rule (defaults to allowed)
#
# -----------------------------------------------------------
# TEST CASES TO IMPLEMENT:
#
#   extract_text():
#   - test_extract_text_removes_scripts: script tags removed from output
#   - test_extract_text_removes_nav: nav/header/footer content removed
#   - test_extract_text_keeps_body: main body content preserved
#   - test_extract_text_empty_html: returns empty string for empty input
#
#   detect_page_type():
#   - test_detect_product_page: URL "/p/12345" → PRODUCT_PAGE
#   - test_detect_faq_page: URL "/faq" → FAQ_PAGE
#   - test_detect_policy_page: URL "/return-policy" → POLICY_PAGE
#   - test_detect_homepage: URL "/" → HOMEPAGE
#   - test_detect_unknown: unrecognized URL pattern → None or LANDING_PAGE
#
#   check_robots_for_gptbot():
#   - test_robots_allows_gptbot: parses SAMPLE_ROBOTS_ALLOW → returns True
#   - test_robots_blocks_gptbot: parses SAMPLE_ROBOTS_BLOCK → returns False
#   - test_robots_no_gptbot_rule: no GPTBot section → defaults to True (allowed)
#   - test_robots_fetch_failure: httpx raises exception → returns True (assume allowed)
#   NOTE: Mock httpx.get to return sample robots.txt content
#
#   audit_page():
#   - test_audit_page_200: successful fetch with Product schema → PageAudit with has_schema=True
#   - test_audit_page_404: 404 response → PageAudit with http_status=404
#   - test_audit_page_no_schema: page with no JSON-LD → has_schema=False, has_valid_schema=False
#   - test_audit_page_invalid_schema: malformed JSON-LD → has_schema=True, has_valid_schema=False, schema issues created
#   - test_audit_page_word_count: word_count_bot matches extracted text word count
#   NOTE: Mock httpx.get to return SAMPLE_PRODUCT_HTML
#
#   crawl_company():
#   - test_crawl_company_success: crawls 3 mock pages → CrawlJob.status=COMPLETED, pages_crawled=3
#   - test_crawl_company_bot_blocked: robots.txt blocks GPTBot → bot_blocked=True, Company.bot_allowed=False
#   - test_crawl_company_sitemap_missing: no sitemap.xml → falls back to homepage link crawl
#   NOTE: Mock all httpx.get calls to return predefined responses
