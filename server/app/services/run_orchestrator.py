# app/services/run_orchestrator.py
# -----------------------------------------
# Orchestration layer for user-triggered asynchronous runs.
# Replaces scheduler-based daily/weekly automation with explicit
# per-company execution started from frontend.
#
# IMPORTS NEEDED:
#   from datetime import datetime, timezone
#   import threading
#   from app.extensions import db
#   from app.models.query import QueryTemplate, QueryRun, LLMPlatform, RunStatus
#   from app.models.run_history import QueryBatchRun, QueryBatchItem, BatchStatus, BatchItemStatus
#   from app.services.query_runner import run_single_query
#   from app.services.fact_checker import check_query_run
#   from app.services.scoring import update_all_scores
#
# -----------------------------------------------------------
# FUNCTION: suggest_prompts_for_topic(company, topic: str, query_count: int) -> list[str]
# -----------------------------------------------------------
# PURPOSE:
#   Generate company-aware prompt suggestions.
#
# STRATEGY:
#   1. Pull active QueryTemplate rows for company related to topic.
#   2. Add topic-specific variations ("best", "under price", "for beginners", brand compare).
#   3. Deduplicate and return exact requested count.
#
# -----------------------------------------------------------
# FUNCTION: create_draft_batch(company, user, topic: str, prompts: list[str]) -> QueryBatchRun
# -----------------------------------------------------------
# PURPOSE:
#   Create run history parent row + draft query items before execution.
#
# -----------------------------------------------------------
# FUNCTION: update_batch_queries(run_id: int, edited_queries: list[str], edited_by_user_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Replace/edit query items before start.
#   Maintains prompt order for deterministic execution.
#
# -----------------------------------------------------------
# FUNCTION: enqueue_batch_execution(run_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Switch batch status to queued and start non-blocking worker thread.
#
# NOTE:
#   In production, this function should delegate to Celery/RQ/SQS worker.
#   Current backend scaffolding uses threading for simple async behavior.
#
# -----------------------------------------------------------
# FUNCTION: _execute_batch_run(run_id: int)
# -----------------------------------------------------------
# PURPOSE:
#   Internal worker function.
#
# STEPS:
#   1. Set batch status=running, started_at.
#   2. Capture before_snapshot scores.
#   3. Iterate query items:
#       - For each platform enabled for company:
#         a. Create QueryRun row (pending->running).
#         b. Call run_single_query(...).
#         c. Save output and set status completed/failed.
#         d. Trigger check_query_run for accuracy/error tracking.
#       - Mark item status and progress counters.
#   4. Recalculate company scores.
#   5. Capture after_snapshot.
#   6. Mark batch completed/failed with summary payload.
#
# -----------------------------------------------------------
# FUNCTION: get_batch_progress(run_id: int) -> dict
# -----------------------------------------------------------
# PURPOSE:
#   Return normalized progress object for frontend polling.
#
# RETURNS:
#   {
#     "run_id": int,
#     "status": "queued|running|completed|failed",
#     "total_queries": int,
#     "completed_queries": int,
#     "failed_queries": int,
#     "progress_pct": float
#   }
