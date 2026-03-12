# app/jobs/score_updater.py
# -----------------------------------------
# Background job: Recalculates scores after query batches
# and measures fix impact for published ContentFixes.
# Called by daily_queries.py after each batch, and also
# runs on its own schedule every 6 hours to catch any drift.
#
# IMPORTS NEEDED:
#   from app import create_app
#   from app.extensions import db
#   from app.models.company import Company
#   from app.models.content import ContentFix, FixStatus, PublishedFix
#   from app.services.scoring import update_all_scores, measure_fix_impact
#   import logging
#   from datetime import datetime, timezone, timedelta
#
# -----------------------------------------------------------
# FUNCTION: run_score_updater()
# -----------------------------------------------------------
# PURPOSE:
#   Scheduled job that recalculates all company scores
#   and triggers impact measurement for mature ContentFixes.
#
# EXECUTION PIPELINE:
#   1. Create Flask app context
#
#   2. For each company:
#         a. Call update_all_scores(company.id)
#            - Updates Company.ai_visibility_score, accuracy_score, top_rec_rate, open_error_count
#         b. Log new scores for monitoring
#
#   3. Find all published ContentFixes where:
#         - status = PUBLISHED
#         - published_at <= 30 days ago
#         - impact has not yet been measured (PublishedFix.impact_measured = False)
#
#   4. For each qualifying fix:
#         a. Call measure_fix_impact(fix.id) → score_delta
#         b. Update PublishedFix.impact_measured = True, score_delta = result
#         c. Log: "Fix #[id] impact: [before] → [after] (+[delta])"
#
#   5. Commit all changes
#
# -----------------------------------------------------------
# FUNCTION: update_scores_for_company(company_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Recalculates scores for a single company.
#   Called directly by daily_queries.py after each company's batch completes
#   so scores are fresh immediately after runs finish.
#
# STEPS:
#   1. Call update_all_scores(company_id)
#   2. Log updated scores
#   3. Return the score dict for logging in daily_queries.py
#
# -----------------------------------------------------------
# FUNCTION: check_citation_source_accuracy(company_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Reviews CitationSource records for this company and flags any
#   domains that have recently caused FactualErrors.
#   Sets CitationSource.accuracy_concern = True for problematic sources.
#
# LOGIC:
#   1. Query SourceMention rows where caused_error = True in last 30 days
#   2. Group by source_id, count occurrences
#   3. If a source has caused 3+ errors: set accuracy_concern = True
#   4. Update CitationSource.negative_count with fresh count
