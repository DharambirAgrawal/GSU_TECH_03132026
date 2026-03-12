# app/jobs/__init__.py
# -----------------------------------------
# Legacy package retained for compatibility.
#
# IMPORTANT:
#   Scheduler-driven daily/weekly automation is intentionally removed.
#   Execution is now user-triggered from frontend and orchestrated through:
#     - app/routes/runs.py
#     - app/services/run_orchestrator.py
#
# If background workers are introduced (Celery/RQ), worker bootstrap
# modules can be added here later without reintroducing cron-style app jobs.
