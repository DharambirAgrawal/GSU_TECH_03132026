# app/routes/ethics.py
# -----------------------------------------
# Blueprint for ethics and compliance monitoring endpoints.
# Registered in create_app() at URL prefix: /api/ethics
#
# IMPORTS NEEDED:
#   from flask import Blueprint, jsonify, request
#   from app.models.company import Company
#   from app.models.ethics import EthicsFlag, ComplianceAlert, EthicsCategory, AlertStatus
#   from app.extensions import db
#   from datetime import datetime, timezone
#
# BLUEPRINT:
#   bp = Blueprint("ethics", __name__)
#
# -----------------------------------------------------------
# ROUTE 1: GET /api/ethics/<company_slug>
# -----------------------------------------------------------
# PURPOSE:
#   Returns the Ethics Scorecard — aggregated compliance status.
#   Shows how many open flags exist, by category, and overall risk level.
#
# LOGIC:
#   1. Look up Company by slug
#   2. Count EthicsFlags by alert_status (open, alerted, reviewing, resolved)
#   3. Count by EthicsCategory to show breakdown (financial_misinformation, discriminatory_content, etc.)
#   4. Count by severity (critical, high, medium, low)
#   5. Identify any CRITICAL flags that are still OPEN — these need immediate attention
#   6. Return summary + list of most recent open flags (limit 10)
#
# RESPONSE SHAPE:
#   {
#     "company": "Capital One",
#     "risk_level": "high",   // "low", "medium", "high", "critical"
#     "open_flags": 3,
#     "by_status": { "open": 3, "reviewing": 1, "resolved": 12 },
#     "by_category": {
#       "financial_misinformation": 2,
#       "undisclosed_limitation": 1
#     },
#     "critical_unresolved": [ { ...ethics_flag.to_dict() } ],
#     "recent_flags": [ { ...ethics_flag.to_dict() } ]
#   }
#
# -----------------------------------------------------------
# ROUTE 2: GET /api/ethics/<company_slug>/flags
# -----------------------------------------------------------
# PURPOSE:
#   Returns the full list of EthicsFlags with filtering and pagination.
#
# QUERY PARAMS:
#   - status: string (optional) — filter by AlertStatus
#   - category: string (optional) — filter by EthicsCategory
#   - severity: string (optional) — filter by severity
#   - page: int (default 1)
#   - per_page: int (default 25)
#
# LOGIC:
#   1. Build query with optional filters
#   2. Order by severity DESC, then flagged_at DESC (worst/newest first)
#   3. Return paginated results with total count
#
# -----------------------------------------------------------
# ROUTE 3: PATCH /api/ethics/flags/<flag_id>/status
# -----------------------------------------------------------
# PURPOSE:
#   Update the status of an EthicsFlag.
#   Used when the compliance team takes action on a flag.
#
# REQUEST BODY:
#   {
#     "status": "reviewing" | "resolved" | "escalated",
#     "reviewed_by": "compliance@company.com",
#     "resolution_summary": "Verified with legal — not a CFPB violation."
#   }
#
# LOGIC:
#   1. Look up EthicsFlag by id
#   2. Update alert_status, reviewed_by, resolution_summary
#   3. If new status = RESOLVED: set resolved_at = now()
#   4. Commit and return updated flag
#
# -----------------------------------------------------------
# ROUTE 4: POST /api/ethics/flags/<flag_id>/alert
# -----------------------------------------------------------
# PURPOSE:
#   Manually trigger a compliance alert email for a specific flag.
#   Auto-alerts happen for CRITICAL severity flags, but this allows
#   manual escalation of HIGH flags.
#
# LOGIC:
#   1. Look up EthicsFlag by id
#   2. Get alert_email from Company's CompanyConfig
#   3. Build alert email subject and body with flag details
#   4. Send email (via SMTP or SendGrid — configured in config.py)
#   5. Create ComplianceAlert record to log the send
#   6. Update EthicsFlag.alert_status = ALERTED, alerted_at = now()
#   7. Return success with ComplianceAlert id
#
# ERROR HANDLING:
#   - 404 if company or flag not found
#   - 400 if invalid status transition
#   - 500 if email delivery fails (still create ComplianceAlert with delivery_status = "failed")
