#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$REPO_ROOT/clean_project_extracted/1-hour"
PID_FILE="$BASE_DIR/run/bot.pid"

if [ -f "$PID_FILE" ]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping bot (pid $PID) with SIGTERM..."
    kill -15 "$PID" || true
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
      echo "Process did not exit, sending SIGKILL..."
      kill -9 "$PID" || true
    fi
  else
    echo "PID file exists but process $PID is not running. Cleaning up PID file."
  fi
  rm -f "$PID_FILE"
  echo "Stopped."
else
  echo "PID file not found — trying pkill by path..."
  pkill -f "$BASE_DIR/main.py" || echo "No process found by path."
fi
