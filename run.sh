#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-both}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$ROOT_DIR/server"
CLIENT_DIR="$ROOT_DIR/client"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN=""

detect_python() {
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  else
    echo "[run.sh] Python not found. Install Python 3 and try again."
    exit 1
  fi
}

ensure_python_env() {
  detect_python

  if [ ! -d "$VENV_DIR" ]; then
    echo "[run.sh] Creating Python virtual environment at $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
  fi

  if [ -f "$VENV_DIR/Scripts/activate" ]; then
    source "$VENV_DIR/Scripts/activate"
  elif [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
  else
    echo "[run.sh] Could not find venv activation script in $VENV_DIR"
    exit 1
  fi
}

install_server_deps() {
  ensure_python_env
  echo "[run.sh] Installing server dependencies..."
  pip install -r "$SERVER_DIR/requirements.txt"
}

install_client_deps() {
  echo "[run.sh] Installing client dependencies..."
  (cd "$CLIENT_DIR" && npm install)
}

run_server() {
  install_server_deps
  echo "[run.sh] Starting Flask app on http://localhost:5000 ..."
  cd "$SERVER_DIR"
  python run.py
}

run_worker() {
  install_server_deps
  echo "[run.sh] Starting Celery worker..."
  cd "$SERVER_DIR"
  celery -A celery_worker.celery_app worker --loglevel=info
}

run_client() {
  install_client_deps
  echo "[run.sh] Starting Vite client on http://localhost:5173 ..."
  cd "$CLIENT_DIR"
  npm run dev -- --host 0.0.0.0 --port 5173
}

run_both() {
  install_server_deps
  install_client_deps

  echo "[run.sh] Starting Flask app on http://localhost:5000 ..."
  (
    cd "$SERVER_DIR"
    python run.py
  ) &
  SERVER_PID=$!

  echo "[run.sh] Starting Vite client on http://localhost:5173 ..."
  (
    cd "$CLIENT_DIR"
    npm run dev -- --host 0.0.0.0 --port 5173
  ) &
  CLIENT_PID=$!

  cleanup() {
    echo "[run.sh] Shutting down processes..."
    kill "$SERVER_PID" "$CLIENT_PID" 2>/dev/null || true
    wait "$SERVER_PID" "$CLIENT_PID" 2>/dev/null || true
  }

  trap cleanup INT TERM EXIT
  wait "$SERVER_PID" "$CLIENT_PID"
}

case "$MODE" in
  server)
    run_server
    ;;
  client)
    run_client
    ;;
  worker)
    run_worker
    ;;
  both)
    run_both
    ;;
  *)
    echo "Usage: bash run.sh [server|client|worker|both]"
    exit 1
    ;;
esac
