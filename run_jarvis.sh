#!/usr/bin/env bash
set -euo pipefail

# Simple launcher: activates venv, loads .env, enables wake mode, and starts Jarvis.
# Usage: ./run_jarvis.sh

# Always run from the repo directory regardless of where the script was invoked
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv if present
if [[ -f "jarvisai-venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "jarvisai-venv/bin/activate"
else
  echo "[run] venv not found. Creating one and installing requirements…"
  if ! command -v python3 >/dev/null 2>&1; then
    echo "[run] python3 not found on PATH. Install Python 3 and try again." >&2
    exit 1
  fi
  python3 -m venv jarvisai-venv
  # shellcheck disable=SC1091
  source "jarvisai-venv/bin/activate"
  pip install -r requirements.txt
fi

# Do not source .env here; jarvis.py loads it via python-dotenv.

# Force wake mode unless explicitly disabled
export WAKE_MODE=${WAKE_MODE:-1}
# Fast kill on shutdown by default (Jarvis will call os._exit(0) after closing audio)
export FAST_SHUTDOWN=${FAST_SHUTDOWN:-1}
# Make Python stdout unbuffered for immediate logs
export PYTHONUNBUFFERED=1

echo "[run] Starting Jarvis (wake mode=$WAKE_MODE)…"
python jarvis.py