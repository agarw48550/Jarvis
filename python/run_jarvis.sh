#!/bin/bash
# 🤖 JARVIS CLI - One-command startup script
#
# Usage: ./run_jarvis.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "🤖 Starting Jarvis CLI..."
echo ""

# Check if Python 3.11 is available
if command -v python3.11 &> /dev/null; then
    PYTHON=python3.11
elif command -v python3 &> /dev/null; then
    PYTHON=python3
else
    echo "❌ Python 3 not found. Please install Python 3.11+"
    exit 1
fi

echo "📦 Using $PYTHON"

# Check if dependencies are installed, install if not
$PYTHON -c "import dotenv, requests, pyttsx3" 2>/dev/null || {
    echo "📦 Installing dependencies..."
    $PYTHON -m pip install python-dotenv requests pyttsx3 --quiet
}

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  No .env file found!"
    echo "   Creating from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "   Created .env from .env.example"
        echo "   Please edit .env with your API keys!"
        echo ""
    fi
fi

# Run Jarvis CLI
echo ""
$PYTHON jarvis_cli.py
