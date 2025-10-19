import requests

WIKI_API = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"


def _clean_text(text: str) -> str:
    s = (text or "").strip()
    # Keep it short for TTS
    if len(s) > 500:
        s = s[:500].rsplit(".", 1)[0] + "."
    return s


def summary(topic: str) -> str:
    q = (topic or "").strip()
    if not q:
        return "Missing topic."
    try:
        url = WIKI_API + requests.utils.quote(q)
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            txt = data.get("extract") or data.get("description") or ""
            return _clean_text(txt) or "No summary found."
        if r.status_code == 404:
            return "No summary found."
    except Exception:
        pass
    return "Lookup failed."


def search(query: str, limit: int = 3) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": q,
            "format": "json",
            "srlimit": str(limit),
        }
        r = requests.get(WIKI_SEARCH, params=params, timeout=6)
        if r.status_code == 200:
            data = r.json()
            items = data.get("query", {}).get("search", []) or []
            return [{"title": it.get("title", ""), "snippet": it.get("snippet", "")} for it in items]
    except Exception:
        return []
    return []
