import os
import json
import time
from typing import List, Dict


DEFAULT_MEMORY_FILE = os.getenv("MEMORY_FILE", "data/memories.json")


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)


def _load(path: str = DEFAULT_MEMORY_FILE) -> List[Dict]:
    try:
        if not os.path.exists(path):
            return []
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def _save(items: List[Dict], path: str = DEFAULT_MEMORY_FILE):
    try:
        _ensure_dir(path)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def add_memory(text: str) -> str:
    if not text or not text.strip():
        return "Nothing to remember."
    items = _load()
    ts = int(time.time())
    items.append({"ts": ts, "text": text.strip()})
    # keep file from growing without bound
    max_items = 500
    if len(items) > max_items:
        items = items[-max_items:]
    _save(items)
    return "Got it. I’ll remember that."


def search_memories(query: str, limit: int = 5) -> List[str]:
    items = _load()
    q = (query or "").strip().lower()
    if not q:
        return [it["text"] for it in items[-limit:]]
    hits = [it["text"] for it in items if q in it.get("text", "").lower()]
    return hits[:limit]


def clear_memories() -> str:
    _save([])
    return "Cleared all memories."
