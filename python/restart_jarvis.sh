#!/bin/bash

# Get the directory where this script is located
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PYTHON_EXEC="$PROJECT_DIR/venv/bin/python3"
SCRIPT_NAME="jarvis_menu.py"

# Navigate to directory
cd "$PROJECT_DIR" || exit 1

# Optional: Pull updates if requested
if [ "$1" == "--update" ]; then
    echo "⬇️ Pulling latest updates from GitHub..."
    git pull
    # Re-run install logic if requirements changed
    ./venv/bin/pip install -r requirements.txt
fi

echo "🛑 Stopping existing Jarvis instances..."
# Kill any process matching jarvis_menu.py
pkill -f "$SCRIPT_NAME"

# Wait a moment
sleep 1

echo "🚀 Starting Jarvis..."
# Run in background
nohup "$PYTHON_EXEC" -u "$SCRIPT_NAME" > jarvis_debug.log 2>&1 &
echo "📋 Logs are being written to $PROJECT_DIR/jarvis_debug.log"

echo "✅ Jarvis restarted successfully!"
