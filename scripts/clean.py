#!/usr/bin/env python3
"""Repo cleanup utility.
- Removes __pycache__ directories and *.pyc files
- Removes .DS_Store files
- Removes stray *.mp3 in project root (from TTS fallbacks)
- Keeps venv, credentials, and tokens
"""
import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEEP_DIRS = {ROOT / 'jarvisai-venv'}

REMOVE_PATTERNS = [
    ('__pycache__', 'dir'),
    ('.DS_Store', 'file'),
    ('*.pyc', 'glob'),
    ('*.pyo', 'glob'),
    ('*.mp3', 'glob'),
]

EXCLUDE_DIRS = {'jarvisai-venv', '.git', '.idea', '.vscode'}


def safe_remove(path: Path):
    try:
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink(missing_ok=True)
    except Exception:
        pass


def main():
    for root, dirs, files in os.walk(ROOT):
        # Skip excluded directories
        parts = set(Path(root).parts)
        if any(x in parts for x in EXCLUDE_DIRS):
            continue
        # Remove __pycache__ directories
        for name, kind in REMOVE_PATTERNS:
            if kind == 'dir' and name in dirs:
                p = Path(root) / name
                safe_remove(p)
        # Remove matching files
        if 'file' in [k for _, k in REMOVE_PATTERNS]:
            if '.DS_Store' in files:
                safe_remove(Path(root) / '.DS_Store')
        # Glob patterns
        for pattern, kind in REMOVE_PATTERNS:
            if kind != 'glob':
                continue
            for p in Path(root).glob(pattern):
                # Keep anything inside venv
                if any(str(p).startswith(str(k)) for k in KEEP_DIRS):
                    continue
                safe_remove(p)

if __name__ == '__main__':
    main()
