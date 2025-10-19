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
