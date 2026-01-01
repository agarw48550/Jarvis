#!/usr/bin/env python3
"""
🤖 JARVIS CLI - Legacy Entry Point
Redirects to new modular CLI interface
"""

import sys
from pathlib import Path

# Redirect to new CLI
sys.path.insert(0, str(Path(__file__).parent))
from interfaces.cli import main

if __name__ == "__main__":
    main()
