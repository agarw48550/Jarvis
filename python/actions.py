#!/usr/bin/env python3
"""
Jarvis Actions - Real tool execution
"""

import os
import subprocess
import webbrowser
import json
import urllib.parse
import requests
from datetime import datetime
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent / "reminders.json"


def search_web(query: str, open_browser: bool = False) -> str:
    """
    Search the web. If open_browser=False, tries to get actual results.
    Falls back to opening browser if no API available.
    """
    # Try DuckDuckGo Instant Answer API (free, no key needed)
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        # Check for instant answer
        if data.get("AbstractText"):
            return data["AbstractText"][:300]
        
        # Check for related topics
        if data.get("RelatedTopics") and len(data["RelatedTopics"]) > 0:
            results = []
            for topic in data["RelatedTopics"][:3]:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(topic["Text"][:100])
            if results:
                return "Here's what I found: " + " | ".join(results)
    except:
        pass
    
    # Fallback: open browser
    search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
    webbrowser.open(search_url)
    return f"I've opened a search for '{query}' in your browser."


def open_app(app_name: str) -> str:
    """Open application on macOS"""
    app = app_name.strip().rstrip('.').title()
    
    # Common mappings
    mappings = {
        "Safari": "Safari", "Chrome": "Google Chrome", "Firefox": "Firefox",
        "Notes": "Notes", "Notion": "Notion", "Spotify": "Spotify",
        "Slack": "Slack", "Discord": "Discord", "Terminal": "Terminal",
        "Finder": "Finder", "Messages": "Messages", "Mail": "Mail",
        "Calendar": "Calendar", "Music": "Music", "Photos": "Photos",
        "Settings": "System Settings", "Vscode": "Visual Studio Code",
        "Code": "Visual Studio Code", "Word": "Microsoft Word",
        "Excel": "Microsoft Excel", "Powerpoint": "Microsoft PowerPoint",
    }
    
    actual_app = mappings.get(app, app)
    
    try:
        result = subprocess.run(["open", "-a", actual_app],
                                capture_output=True, timeout=5)
        if result.returncode == 0:
            return f"Opened {actual_app}."
        return f"Couldn't find {app}."
    except:
        return f"Error opening {app}."


def get_time() -> str:
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def set_volume(level: int = None, action: str = None) -> str:
    """Control volume - by percentage or action"""
    try:
        if level is not None:
            level = max(0, min(100, level))
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"],
                          check=True, timeout=5)
            return f"Volume set to {level}%."
        
        if action == "up":
            subprocess.run(["osascript", "-e",
                "set volume output volume ((output volume of (get volume settings)) + 15)"],
                check=True, timeout=5)
            return "Volume up."
        
        if action == "down":
            subprocess.run(["osascript", "-e",
                "set volume output volume ((output volume of (get volume settings)) - 15)"],
                check=True, timeout=5)
            return "Volume down."
        
        if action == "mute":
            subprocess.run(["osascript", "-e", "set volume output muted true"],
                          check=True, timeout=5)
            return "Muted."
        
        if action == "unmute":
            subprocess.run(["osascript", "-e", "set volume output muted false"],
                          check=True, timeout=5)
            return "Unmuted."
        
        return "Specify volume level (0-100) or action (up/down/mute)."
    except Exception as e:
        return f"Volume control failed: {e}"


def add_reminder(text: str) -> str:
    reminders = load_reminders()
    reminders.append({"text": text, "created": datetime.now().isoformat()})
    save_reminders(reminders)
    return f"I'll remind you: {text}"


def get_reminders() -> str:
    reminders = load_reminders()
    if not reminders:
        return "You have no reminders."
    lines = [f"{i+1}. {r['text']}" for i, r in enumerate(reminders)]
    return "Your reminders:\n" + "\n".join(lines)


def clear_reminders() -> str:
    save_reminders([])
    return "All reminders cleared."


def load_reminders() -> list:
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text())
        except:
            return []
    return []


def save_reminders(r: list):
    REMINDERS_FILE.write_text(json.dumps(r, indent=2))


def pause_listening() -> str:
    return "PAUSE_LISTENING"


def resume_listening() -> str:
    return "RESUME_LISTENING"


# Tool definitions for LLM
TOOLS = {
    "search_web": {
        "function": search_web,
        "description": "Search the web for information",
        "parameters": {"query": "string"}
    },
    "open_app": {
        "function": open_app,
        "description": "Open an application",
        "parameters": {"app_name": "string"}
    },
    "get_time": {
        "function": get_time,
        "description": "Get current time and date",
        "parameters": {}
    },
    "set_volume": {
        "function": set_volume,
        "description": "Control system volume",
        "parameters": {"level": "int (0-100)", "action": "up/down/mute/unmute"}
    },
    "add_reminder": {
        "function": add_reminder,
        "description": "Add a reminder",
        "parameters": {"text": "string"}
    },
    "get_reminders": {
        "function": get_reminders,
        "description": "List all reminders",
        "parameters": {}
    },
    "clear_reminders": {
        "function": clear_reminders,
        "description": "Clear all reminders",
        "parameters": {}
    },
    "pause_listening": {
        "function": pause_listening,
        "description": "Stop listening temporarily",
        "parameters": {}
    },
}
