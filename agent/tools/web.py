import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from typing import List, Dict


def _normalize_url(raw: str) -> str:
    """Turn DuckDuckGo redirect or protocol-relative URLs into direct https URLs."""
    if not raw:
        return raw
    try:
        # Protocol-relative URLs (e.g., //duckduckgo.com/...)
        if raw.startswith("//"):
            raw = "https:" + raw
        # If it's a DDG redirect, pull real target from 'uddg' param
        parsed = urlparse(raw)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            qs = parse_qs(parsed.query)
            if "uddg" in qs:
                target = qs.get("uddg", [""])[0]
                target = unquote(target)
                # Ensure scheme
                if target.startswith("//"):
                    target = "https:" + target
                if not target.startswith("http"):
                    target = "https://" + target
                return target
        # Ensure scheme if missing
        if not raw.startswith("http"):
            return "https://" + raw.lstrip("/")
        return raw
    except Exception:
        return raw


def search(query: str, k: int = 5) -> List[Dict[str, str]]:
    """Simple DuckDuckGo HTML search (no API key)."""
    try:
        params = {"q": query}
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get("https://duckduckgo.com/html/", params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        out: List[Dict[str, str]] = []
        for a in soup.select("a.result__a"):
            title = a.get_text(strip=True)
            url = a.get("href")
            if title and url:
                out.append({"title": title, "url": _normalize_url(url)})
                if len(out) >= k:
                    break
        # Prefer reputable sources when present
        def rank(item):
            u = item.get("url", "")
            host = urlparse(u).netloc.lower() if u else ""
            score = 0
            if any(h in host for h in ("wikipedia.org", "espncricinfo.com", "icc-cricket.com")):
                score += 10
            return -score
        return sorted(out, key=rank)
    except Exception:
        return []


essential_tags = {"p", "h1", "h2", "h3", "li"}


def fetch_text(url: str) -> str:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        # Remove scripts/styles
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        texts = []
        for tag in soup.find_all(essential_tags):
            txt = tag.get_text(separator=" ", strip=True)
            if txt:
                texts.append(txt)
        joined = "\n".join(texts)
        return joined.strip() or soup.get_text(" ", strip=True)
    except Exception as e:
        return f"Fetch error: {e}"
