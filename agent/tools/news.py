import os
import urllib.request
import xml.etree.ElementTree as ET


def _default_feeds() -> list[str]:
    # Comma-separated list from env, else a few defaults
    env = os.getenv("NEWS_FEEDS", "").strip()
    if env:
        return [u.strip() for u in env.split(",") if u.strip()]
    return [
        "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://rss.cnn.com/rss/edition.rss",
    ]


def headlines(limit: int = 5) -> list[str]:
    items: list[str] = []
    for url in _default_feeds():
        if len(items) >= limit:
            break
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = resp.read()
            root = ET.fromstring(data)
            for item in root.findall(".//item"):
                title_el = item.find("title")
                if title_el is not None and title_el.text:
                    title = title_el.text.strip()
                    if title and title not in items:
                        items.append(title)
                        if len(items) >= limit:
                            break
        except Exception:
            continue
    return items[:limit]
