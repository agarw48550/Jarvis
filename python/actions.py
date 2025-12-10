#!/usr/bin/env python3
"""
Jarvis Actions - Fixed for macOS
"""

import os
import subprocess
import webbrowser
import json
import urllib.parse
from datetime import datetime
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent / "reminders.json"


def search_web(query: str) -> str:
    """Open web search in default browser"""
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}"
    webbrowser.open(url)
    return f"Searching for '{query}'."


def open_app(app_name: str) -> str:
    """Open an application on macOS"""
    # Clean up the app name
    app = app_name.strip().rstrip('.')
    
    # Common app name mappings
    app_mappings = {
        "safari": "Safari",
        "chrome": "Google Chrome",
        "firefox": "Firefox",
        "notes": "Notes",
        "notion": "Notion",
        "spotify": "Spotify",
        "slack": "Slack",
        "discord": "Discord",
        "terminal": "Terminal",
        "finder": "Finder",
        "messages": "Messages",
        "mail": "Mail",
        "calendar": "Calendar",
        "music": "Music",
        "photos": "Photos",
        "settings": "System Preferences",
        "preferences": "System Preferences",
        "vscode": "Visual Studio Code",
        "code": "Visual Studio Code",
    }
    
    # Try to find the correct app name
    app_lower = app.lower()
    actual_app = app_mappings.get(app_lower, app)
    
    try:
        # Method 1: Direct open -a
        result = subprocess.run(
            ["open", "-a", actual_app],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return f"Opened {actual_app}."
        
        # Method 2: Try with .app extension
        result = subprocess.run(
            ["open", "-a", f"{actual_app}.app"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            return f"Opened {actual_app}."
        
        # Method 3: Use mdfind to locate the app
        find_result = subprocess.run(
            ["mdfind", f"kMDItemKind == 'Application' && kMDItemDisplayName == '*{app}*'c"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if find_result.stdout.strip():
            app_path = find_result.stdout.strip().split('\n')[0]
            subprocess.run(["open", app_path], check=True, timeout=5)
            return f"Opened {os.path.basename(app_path)}."
        
        return f"Couldn't find '{app}'. Try the exact app name."
        
    except subprocess.TimeoutExpired:
        return f"Timeout opening {app}."
    except Exception as e:
        return f"Error opening {app}: {e}"


def get_time() -> str:
    """Get current time and date"""
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def control_volume(action: str) -> str:
    """Control system volume on macOS"""
    try:
        if action == "up":
            script = 'set volume output volume ((output volume of (get volume settings)) + 15)'
            subprocess.run(["osascript", "-e", script], check=True, timeout=5)
            return "Volume up."
        
        elif action == "down":
            script = 'set volume output volume ((output volume of (get volume settings)) - 15)'
            subprocess.run(["osascript", "-e", script], check=True, timeout=5)
            return "Volume down."
        
        elif action == "mute":
            subprocess.run(["osascript", "-e", "set volume output muted true"], check=True, timeout=5)
            return "Muted."
        
        elif action == "unmute":
            subprocess.run(["osascript", "-e", "set volume output muted false"], check=True, timeout=5)
            return "Unmuted."
        
        elif action == "max":
            subprocess.run(["osascript", "-e", "set volume output volume 100"], check=True, timeout=5)
            return "Volume at maximum."
        
        return f"Unknown volume action: {action}"
        
    except Exception as e:
        return f"Volume control failed: {e}"


def set_reminder(text: str) -> str:
    """Save a reminder"""
    reminders = load_reminders()
    reminders.append({
        "text": text,
        "created": datetime.now().isoformat()
    })
    save_reminders(reminders)
    return f"I'll remember: {text}"


def get_reminders() -> str:
    """Get all reminders"""
    reminders = load_reminders()
    if not reminders:
        return "No reminders set."
    
    lines = ["Your reminders:"]
    for i, r in enumerate(reminders, 1):
        lines.append(f"  {i}. {r['text']}")
    return "\n".join(lines)


def clear_reminders() -> str:
    """Clear all reminders"""
    save_reminders([])
    return "Reminders cleared."


def load_reminders() -> list:
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text())
        except:
            return []
    return []


def save_reminders(reminders: list):
    REMINDERS_FILE.write_text(json.dumps(reminders, indent=2))


# Action registry
ACTIONS = {
    "search": search_web,
    "open": open_app,
    "time": get_time,
    "volume": control_volume,
    "remind": set_reminder,
    "reminders": get_reminders,
    "clear_reminders": clear_reminders,
}
