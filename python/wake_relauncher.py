#!/usr/bin/env python3
"""
Small helper to relaunch jarvis_menu.py. Intended to be used by a LaunchAgent that triggers on wake.
This script simply starts jarvis_menu.py in the background using the project's venv.
"""
import os
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
PY = BASE / 'venv' / 'bin' / 'python3'
SCRIPT = BASE / 'jarvis_menu.py'

if __name__ == '__main__':
    if not PY.exists():
        print('Error: virtualenv python not found at', PY)
        sys.exit(1)
    if not SCRIPT.exists():
        print('Error: jarvis_menu.py not found at', SCRIPT)
        sys.exit(1)

    subprocess.Popen([str(PY), str(SCRIPT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('Launched jarvis_menu.py')
