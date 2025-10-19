import webbrowser


def open_youtube() -> str:
    try:
        webbrowser.open("https://www.youtube.com")
        return "Opened YouTube."
    except Exception as e:
        return f"Failed to open YouTube: {e}"


def open_github() -> str:
    try:
        webbrowser.open("https://github.com")
        return "Opened GitHub."
    except Exception as e:
        return f"Failed to open GitHub: {e}"


def open_instagram() -> str:
    try:
        webbrowser.open("https://www.instagram.com")
        return "Opened Instagram."
    except Exception as e:
        return f"Failed to open Instagram: {e}"


def yt_trending() -> str:
    try:
        webbrowser.open("https://www.youtube.com/feed/trending")
        return "Opened YouTube Trending."
    except Exception as e:
        return f"Failed to open YouTube Trending: {e}"


def search_youtube(topic: str) -> str:
    topic = (topic or "").strip()
    if not topic:
        return "Missing topic for YouTube search."
    q = "+".join(topic.split())
    url = f"https://www.youtube.com/results?search_query={q}"
    try:
        webbrowser.open(url)
        return f"Searching YouTube for '{topic}'."
    except Exception as e:
        return f"Failed to search YouTube: {e}"


def open_website(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return "Missing website."
    # If it looks like a domain without scheme, add https://
    url = q
    try:
        if not (q.startswith("http://") or q.startswith("https://")):
            if "." in q and " " not in q:
                url = "https://" + q
            else:
                # treat as a search query
                from urllib.parse import quote_plus
                url = f"https://www.google.com/search?q={quote_plus(q)}"
        webbrowser.open(url)
        return f"Opening {url}."
    except Exception as e:
        return f"Failed to open website: {e}"
