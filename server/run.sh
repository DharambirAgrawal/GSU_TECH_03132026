#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-app}"

if [ ! -d "venv" ]; then
  echo "[run.sh] Creating virtual environment..."
  python -m venv venv
fi

if [ -f "venv/Scripts/activate" ]; then
  # Git Bash on Windows
  source venv/Scripts/activate
elif [ -f "venv/bin/activate" ]; then
  # Linux/macOS/WSL
  source venv/bin/activate
else
  echo "[run.sh] Could not find venv activation script."
  exit 1
fi

echo "[run.sh] Installing dependencies..."
pip install -r requirements.txt

if [ "$MODE" = "worker" ]; then
  echo "[run.sh] Starting Celery worker..."
  celery -A celery_worker.celery_app worker --loglevel=info
  exit 0
fi

echo "[run.sh] Starting Flask app on http://localhost:5000 ..."
python run.py
