#!/bin/bash

# Define paths
PROJECT_DIR="/Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis V3/jarvis/python"
PYTHON_EXEC="$PROJECT_DIR/venv/bin/python3"
SCRIPT_NAME="jarvis_menu.py"

# Navigate to directory
cd "$PROJECT_DIR" || exit 1

echo "🛑 Stopping existing Jarvis instances..."
# Kill any process matching jarvis_menu.py
pkill -f "$SCRIPT_NAME"

# Wait a moment
sleep 1

echo "🚀 Starting Jarvis..."
# Run in background
nohup "$PYTHON_EXEC" "$SCRIPT_NAME" > /dev/null 2>&1 &

echo "✅ Jarvis restarted successfully!"
