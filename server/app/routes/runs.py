# app/routes/runs.py
# -----------------------------------------
# Blueprint for user-triggered run lifecycle:
# generate prompts -> optional edit -> start async run -> poll progress.
# Registered in create_app() at URL prefix: /api/runs
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from pydantic import BaseModel, ValidationError, Field
#   from app.extensions import db
#   from app.models.auth import CompanyUser
#   from app.models.query import QueryTemplate
#   from app.models.run_history import QueryBatchRun, QueryBatchItem, BatchStatus
#   from app.services.auth_service import require_company_session
#   from app.services.run_orchestrator import (
#       suggest_prompts_for_topic,
#       create_draft_batch,
#       update_batch_queries,
#       enqueue_batch_execution,
#       get_batch_progress,
#   )
#
# BLUEPRINT:
#   bp = Blueprint("runs", __name__)
#
# -----------------------------------------------------------
# REQUEST MODELS
# -----------------------------------------------------------
# class GeneratePromptsRequest(BaseModel):
#   topic: str
#   query_count: int = Field(default=50, ge=1, le=100)
#
# class UpdateQueriesRequest(BaseModel):
#   queries: list[str]
#
# class StartRunRequest(BaseModel):
#   run_id: int
#
# -----------------------------------------------------------
# ROUTE: POST /api/runs/generate-prompts
# -----------------------------------------------------------
# PURPOSE:
#   Generate company-aware prompt suggestions for a topic and requested count.
#   Example: topic="Laptop", count=50 -> returns 50 draft prompts.
#
# LOGIC:
#   1. Authenticate session and resolve company scope.
#   2. Validate body (topic + query_count).
#   3. Clamp query_count using CompanyConfig.max_query_count.
#   4. suggest_prompts_for_topic(company, topic, query_count).
#   5. create_draft_batch(company, user, topic, prompts).
#   6. Return run draft with editable query list.
#
# RESPONSE:
#   {
#     "run_id": 123,
#     "topic": "Laptop",
#     "query_count": 50,
#     "queries": ["best laptop...", "best laptop from dell..."],
#     "status": "draft"
#   }
#
# -----------------------------------------------------------
# ROUTE: PATCH /api/runs/<run_id>/queries
# -----------------------------------------------------------
# PURPOSE:
#   Allow user edits before execution (replace, reorder, or trim query list).
#
# LOGIC:
#   1. Authenticate and scope to company.
#   2. Validate edited queries.
#   3. Ensure run is still editable (queued/draft, not running).
#   4. update_batch_queries(run_id, edited_queries, user_id).
#   5. Return updated query items.
#
# -----------------------------------------------------------
# ROUTE: POST /api/runs/<run_id>/start
# -----------------------------------------------------------
# PURPOSE:
#   Start asynchronous execution and return immediately.
#   Frontend should not block; it can poll progress endpoint.
#
# LOGIC:
#   1. Authenticate and scope to company.
#   2. Validate run ownership + status.
#   3. enqueue_batch_execution(run_id).
#   4. Return accepted response:
#      { "success": true, "run_id": ..., "status": "queued" }
#
# -----------------------------------------------------------
# ROUTE: GET /api/runs/<run_id>/status
# -----------------------------------------------------------
# PURPOSE:
#   Poll run progress for live updates in frontend.
#
# RESPONSE:
#   {
#     "run_id": 123,
#     "status": "running",
#     "total_queries": 50,
#     "completed_queries": 17,
#     "failed_queries": 1,
#     "progress_pct": 36.0,
#     "started_at": "..."
#   }
#
# -----------------------------------------------------------
# ROUTE: GET /api/runs/history
# -----------------------------------------------------------
# PURPOSE:
#   List company run history for timeline/comparison view.
#   All users in same company see the same history entries.
#
# QUERY PARAMS:
#   - page (default 1)
#   - per_page (default 20)
#   - status (optional)
#
# -----------------------------------------------------------
# ROUTE: GET /api/runs/history/<run_id>
# -----------------------------------------------------------
# PURPOSE:
#   Return full details for one historical run, including query-level results,
#   score snapshot before/after, and comparison metadata.
