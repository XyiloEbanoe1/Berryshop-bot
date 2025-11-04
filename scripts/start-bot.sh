#!/usr/bin/env bash
set -euo pipefail

# Start bot script
# - detects venv python at REPO_ROOT/.venv/bin/python if present
# - runs main.py from the clean_project_extracted/1-hour directory
# - stores PID in run/bot.pid and logs to logs/bot.log

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BASE_DIR="$REPO_ROOT/clean_project_extracted/1-hour"

mkdir -p "$BASE_DIR/logs" "$BASE_DIR/run"

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON="$REPO_ROOT/.venv/bin/python"
else
  PYTHON="$(command -v python3 || command -v python)"
fi

cd "$BASE_DIR"

# If already running, show PID and exit
if [ -f "run/bot.pid" ]; then
  PID=$(cat run/bot.pid)
  if kill -0 "$PID" 2>/dev/null; then
    echo "Bot already running (pid $PID). Use scripts/stop-bot.sh to stop it first." >&2
    exit 0
  else
    echo "Stale PID file found, removing." >&2
    rm -f run/bot.pid
  fi
fi

nohup "$PYTHON" main.py >> logs/bot.log 2>&1 &
PID=$!
# Give it a moment to start
sleep 0.2
echo "$PID" > run/bot.pid

echo "Started bot (pid $PID). Logs: $BASE_DIR/logs/bot.log"
