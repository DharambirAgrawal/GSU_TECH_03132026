# app/services/scoring.py
# -----------------------------------------
# Service: Calculates and updates all visibility and accuracy scores.
# Called by run_orchestrator when a manual run finishes.
# Updates Company cached score fields for fast dashboard loads.
#
# IMPORTS NEEDED:
#   from app.models.company import Company
#   from app.models.query import QueryRun, QueryTemplate
#   from app.models.accuracy import AccuracyCheck, FactualError
#   from app.models.content import ContentFix, PublishedFix
#   from app.extensions import db
#   from sqlalchemy import func, and_
#   from datetime import datetime, timezone, timedelta
#
# -----------------------------------------------------------
# FUNCTION: update_all_scores(company_id: int) -> dict
# -----------------------------------------------------------
# PURPOSE:
#   Recalculates and saves all cached scores for one company.
#   Single entry point called after manual run completion.
#   Returns dict of new score values for logging.
#
# STEPS:
#   1. Call calculate_visibility_score(company_id) → float
#   2. Call calculate_accuracy_score(company_id) → float
#   3. Call calculate_top_rec_rate(company_id) → float
#   4. Count open FactualErrors (is_resolved = False) → int
#   5. Update Company fields: ai_visibility_score, accuracy_score, top_rec_rate, open_error_count
#   6. Commit to db
#   7. Return { "visibility": x, "accuracy": y, "top_rec_rate": z, "open_errors": n }
#
# -----------------------------------------------------------
# FUNCTION: calculate_visibility_score(company_id: int, days: int = 7) -> float
# -----------------------------------------------------------
# PURPOSE:
#   Calculates the AI Visibility Score:
#   % of monitored queries in the last N days where the brand was mentioned.
#
# FORMULA:
#   score = (runs_with_mention / total_runs) * 100
#   - total_runs: count of QueryRun rows for company in last N days with status=COMPLETED
#   - runs_with_mention: count where brand_mentioned = True
#   - Returns 0.0 if total_runs == 0
#
# -----------------------------------------------------------
# FUNCTION: calculate_accuracy_score(company_id: int, days: int = 7) -> float
# -----------------------------------------------------------
# PURPOSE:
#   Calculates the Accuracy Score:
#   % of AI responses with ALL claims correct in the last N days.
#
# FORMULA:
#   score = (accurate_checks / total_checks) * 100
#   - total_checks: count of AccuracyCheck rows linked to company's runs in last N days
#   - accurate_checks: count where overall_accurate = True
#   - Returns 100.0 if no checks (no errors found = fully accurate)
#
# -----------------------------------------------------------
# FUNCTION: calculate_top_rec_rate(company_id: int, days: int = 7) -> float
# -----------------------------------------------------------
# PURPOSE:
#   Calculates the Top Recommendation Rate:
#   % of completed query runs where brand_position = 1 (first recommendation).
#
# FORMULA:
#   score = (position_1_count / total_runs) * 100
#   Counts only QueryRun rows where status = COMPLETED and template expected_brand_mention = True.
#
# -----------------------------------------------------------
# FUNCTION: measure_fix_impact(content_fix_id: int) -> float | None
# -----------------------------------------------------------
# PURPOSE:
#   Calculates the before/after score delta for a ContentFix that has been
#   live for 30+ days. Used to prove ROI of fixes.
#
# LOGIC:
#   1. Load ContentFix — check published_at is 30+ days ago
#   2. before_score is stored on ContentFix at publish time
#   3. Calculate current accuracy/visibility score for the linked query templates
#      (filter QueryRun rows to the target_queries template IDs)
#   4. after_score = current score on those templates
#   5. Update ContentFix.after_score and PublishedFix.score_delta
#   6. Set PublishedFix.impact_measured = True
#   7. Return score_delta (positive = improvement)
#
# -----------------------------------------------------------
# FUNCTION: get_weekly_trend(company_id: int, weeks: int = 8) -> list[dict]
# -----------------------------------------------------------
# PURPOSE:
#   Returns week-by-week visibility and accuracy scores for trend charts.
#   Recalculates from raw QueryRun data (no separate history table required).
#
# LOGIC:
#   1. For each of the last N weeks:
#         - Define week start/end dates
#         - Run calculate_visibility_score with that week's date range
#         - Run calculate_accuracy_score with that week's date range
#   2. Return: [{ "week": "2026-01-05", "visibility": 72.0, "accuracy": 88.0 }, ...]
