#!/bin/bash

# Jarvis Guardian - Auto-Restart Supervisor
# This script keeps Jarvis running even if the process crashes completely.

PROJECT_DIR="$(dirname "$0")"
cd "$PROJECT_DIR" || exit 1

PYTHON_EXEC="./venv/bin/python3"
SCRIPT_NAME="jarvis_menu.py"

echo "🛡️ Starting Jarvis Guardian..."

while true; do
    echo "🚀 Launching Jarvis..."
    "$PYTHON_EXEC" "$SCRIPT_NAME"

    EXIT_CODE=$?
    echo "⚠️ Jarvis exited with code $EXIT_CODE"

    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ Jarvis exited cleanly. Stopping guardian."
        break
    else
        echo "🔄 Crash detected! Restarting in 2 seconds..."
        sleep 2
    fi
done
