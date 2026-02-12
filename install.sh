#!/bin/bash

# Jarvis One-Line Installer
# Usage: ./install.sh

set -e

# ANSI Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}
   ___  __   ___  _  _  ___  ___ 
  | _ \/  \ | _ \| || |/ __|/ __|
  |  _/ /\ \|   /| \/ |\__ \\__ \\
  |_| |_||_||_|_\ \__/ |___/|___/
      JARVIS AI INSTALLER
${NC}"

# 1. Check Pre-requisites
echo -e "\n${BOLD}🔍 Checking system...${NC}"

if [[ "$(uname)" != "Darwin" ]]; then
    echo -e "${RED}❌ Jarvis V3 currently only supports macOS.${NC}"
    exit 1
fi

if ! command -v brew &> /dev/null; then
    echo -e "${RED}❌ Homebrew is not installed. Please install it first: https://brew.sh/${NC}"
    exit 1
fi

# 2. System Dependencies
echo -e "\n${BOLD}📦 Installing system dependencies (portaudio, sox, ffmpeg)...${NC}"
brew install portaudio sox ffmpeg || echo "Dependencies already installed or failed (ignoring)"

# 3. Python Environment
echo -e "\n${BOLD}🐍 Setting up Python environment...${NC}"

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not found."
    exit 1
fi

# Bootstrap SOUL.md if missing
if [ ! -f "python/data/SOUL.md" ]; then
    echo "Creating default SOUL.md..."
    cp "python/data/SOUL.md.example" "python/data/SOUL.md"
fi

# Create venv if not exists
if [ ! -d "python/venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv python/venv
fi

# Activate venv
source python/venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
echo -e "\n${BOLD}⬇️  Installing Python packages...${NC}"
pip install -r python/requirements.txt

# 4. Run Setup Wizard
echo -e "\n${BOLD}🪄  Starting Setup Wizard...${NC}"
python3 python/setup_wizard.py

echo -e "\n${GREEN}${BOLD}✅ Installation Complete!${NC}"
