# app/jobs/weekly_crawl.py
# -----------------------------------------
# Background job: Crawls all company websites weekly to audit AI-readability.
# Scheduled to run every 7 days by APScheduler (registered in create_app).
#
# IMPORTS NEEDED:
#   from app import create_app
#   from app.extensions import db
#   from app.models.company import Company
#   from app.models.crawl import CrawlJob, CrawlStatus
#   from app.services.crawler import crawl_company
#   import logging
#   from datetime import datetime, timezone
#   import threading
#
# -----------------------------------------------------------
# FUNCTION: run_weekly_crawl()
# -----------------------------------------------------------
# PURPOSE:
#   Main job function registered with APScheduler.
#   Crawls every registered company's website.
#
# EXECUTION PIPELINE:
#   1. Create Flask app context
#      with app.app_context():
#
#   2. Get all companies from db
#
#   3. For each company:
#         a. Check if a crawl is already RUNNING (skip if so, log warning)
#         b. Call crawl_company(company.id) → CrawlJob
#         c. After crawl completes:
#               - Sync bot_allowed: Company.bot_allowed = not CrawlJob.bot_blocked
#               - If bot_blocked changed and now False: create a FactualError-like alert
#         d. Log result: "Crawled [company.name]: [pages_crawled] pages, [pages_failed] failed"
#
#   4. Log job completion: "Weekly crawl complete: X companies processed"
#
# ERROR HANDLING:
#   - If crawl_company() raises exception: set CrawlJob.status = FAILED, log traceback
#   - Continue to next company even if one fails
#
# -----------------------------------------------------------
# FUNCTION: trigger_crawl_for_company(company_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Manually triggers a crawl for one company outside the weekly schedule.
#   Called by the POST /api/crawl/<slug>/trigger route.
#   Runs in a background thread so the API can return immediately.
#
# STEPS:
#   1. Create a CrawlJob with status = PENDING for this company
#   2. Spawn a new thread running _crawl_company_thread(company_id, crawl_job_id)
#   3. Return the crawl_job_id so the client can poll for status
#
# -----------------------------------------------------------
# FUNCTION: _crawl_company_thread(company_id: int, crawl_job_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Thread target for manual crawl triggers.
#   Runs crawl_company() in its own Flask app context.
#   Updates CrawlJob status to RUNNING then COMPLETED/FAILED.
#
# NOTE:
#   Must create a fresh Flask app context inside the thread.
#   The app context from the request thread cannot be used in a spawned thread.
