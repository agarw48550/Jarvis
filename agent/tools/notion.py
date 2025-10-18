from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import requests

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers() -> Dict[str, str]:
    token = os.getenv("NOTION_API_KEY", "")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }


def create_page_in_database(database_id: str, title: str, properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "Name": {"title": [{"text": {"content": title}}]},
            **(properties or {}),
        },
    }
    resp = requests.post(f"{NOTION_API_BASE}/pages", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def search(query: str, page_size: int = 5) -> List[Dict[str, Any]]:
    payload = {"query": query, "page_size": page_size}
    resp = requests.post(f"{NOTION_API_BASE}/search", headers=_headers(), json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("results", [])
