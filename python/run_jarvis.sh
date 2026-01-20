#!/bin/bash
# 🤖 JARVIS CLI - One-command startup script
#
# Usage: ./run_jarvis.sh

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "========================================"
echo "      🤖 JARVIS LIVE VOICE CLI        "
echo "========================================"

# Check for virtual environment
if [ -d "venv" ]; then
    echo "✅ Found virtual environment."
    PYTHON_EXEC="./venv/bin/python3"
else
    echo "⚠️  Virtual environment not found in $SCRIPT_DIR/venv"
    echo "📦 Creating virtual environment and installing dependencies..."
    python3 -m venv venv
    ./venv/bin/python3 -m pip install --upgrade pip
    ./venv/bin/python3 -m pip install -r requirements.txt
    PYTHON_EXEC="./venv/bin/python3"
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env from .env.example"
        echo "👉 Please edit .env in $SCRIPT_DIR and add your API keys."
        exit 1
    else
        echo "❌ No .env or .env.example found. Run from a valid Jarvis project directory."
        exit 1
    fi
fi

# Run the Jarvis Live CLI
echo "🚀 Launching Jarvis..."
echo ""
$PYTHON_EXEC jarvis_live_cli.py
