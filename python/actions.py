#!/usr/bin/env python3
"""
Jarvis v7 Actions - Complete Agentic Toolkit
"""

import os
import sys
import subprocess
import webbrowser
import json
import urllib.parse
import requests
import re
from datetime import datetime, timedelta
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent / "reminders.json"

# ============== WEB SEARCH (DuckDuckGo - Free, No API Key) ==============

def search_web(query: str) -> str:
    """Search the web and return actual results (not browser)"""
    try:
        from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        
        if results:
            summaries = []
            for r in results[:3]:
                title = r.get('title', '')
                body = r.get('body', '')[:150]
                summaries.append(f"{title}: {body}")
            
            return "Here's what I found: " + " | ".join(summaries)
        
        return f"I couldn't find results for '{query}'."
        
    except ImportError:
        return "Search unavailable. Install: pip install duckduckgo-search"
    except Exception as e:
        return f"Search error: {e}"


def open_website(url: str) -> str:
    """Open a website in the browser"""
    if not url.startswith('http'):
        url = 'https://' + url
    webbrowser.open(url)
    return f"Opened {url}."


# ============== APPLICATIONS ==============

def open_app(app_name: str) -> str:
    """Open application on macOS"""
    app = app_name.strip().rstrip('.')
    
    mappings = {
        "safari": "Safari", "chrome": "Google Chrome", "firefox": "Firefox",
        "notes": "Notes", "notion": "Notion", "spotify": "Spotify",
        "slack": "Slack", "discord": "Discord", "terminal": "Terminal",
        "finder": "Finder", "messages": "Messages", "mail": "Mail",
        "calendar": "Calendar", "music": "Music", "photos": "Photos",
        "settings": "System Settings", "vscode": "Visual Studio Code",
        "code": "Visual Studio Code", "word": "Microsoft Word",
    }
    
    actual_app = mappings.get(app.lower(), app.title())
    
    try:
        result = subprocess.run(["open", "-a", actual_app],
                               capture_output=True, timeout=5)
        if result.returncode == 0:
            return f"Opened {actual_app}."
        return f"Couldn't find {app}."
    except:
        return f"Error opening {app}."


# ============== TIME & DATE ==============

def get_time() -> str:
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def get_date() -> str:
    now = datetime.now()
    return f"Today is {now.strftime('%A, %B %d, %Y')}."


# ============== VOLUME & SYSTEM ==============

def set_volume(level: int = None, action: str = None) -> str:
    """Control system volume"""
    try:
        if level is not None:
            level = max(0, min(100, level))
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"],
                          check=True, timeout=5)
            return f"Volume set to {level}%."
        
        actions = {
            "up": "set volume output volume ((output volume of (get volume settings)) + 15)",
            "down": "set volume output volume ((output volume of (get volume settings)) - 15)",
            "mute": "set volume output muted true",
            "unmute": "set volume output muted false",
            "max": "set volume output volume 100",
            "min": "set volume output volume 0",
        }
        
        if action in actions:
            subprocess.run(["osascript", "-e", actions[action]], check=True, timeout=5)
            return f"Volume {action}."
        
        return "Specify level (0-100) or action (up/down/mute/unmute)."
    except Exception as e:
        return f"Volume error: {e}"


def take_screenshot(filename: str = None) -> str:
    """Take a screenshot"""
    try:
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.expanduser(f"~/Desktop/{filename}")
        subprocess.run(["screencapture", "-x", path], check=True, timeout=10)
        return f"Screenshot saved to Desktop as {filename}."
    except:
        return "Couldn't take screenshot."


def toggle_wifi(action: str) -> str:
    """Turn wifi on or off"""
    try:
        state = "on" if action == "on" else "off"
        subprocess.run(["networksetup", "-setairportpower", "en0", state], check=True)
        return f"WiFi turned {state}."
    except:
        return "Couldn't control WiFi."


def get_battery() -> str:
    """Get battery status"""
    try:
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        output = result.stdout
        # Parse battery percentage
        match = re.search(r'(\d+)%', output)
        if match:
            percent = match.group(1)
            charging = "charging" if "charging" in output.lower() else "not charging"
            return f"Battery is at {percent}%, {charging}."
        return "Couldn't get battery info."
    except:
        return "Battery info unavailable."


# ============== REMINDERS ==============

def add_reminder(text: str) -> str:
    reminders = load_reminders()
    reminders.append({
        "id": len(reminders) + 1,
        "text": text,
        "created": datetime.now().isoformat(),
        "done": False
    })
    save_reminders(reminders)
    return f"Reminder added: {text}"


def get_reminders() -> str:
    reminders = load_reminders()
    active = [r for r in reminders if not r.get("done")]
    if not active:
        return "You have no reminders."
    lines = [f"{r['id']}. {r['text']}" for r in active]
    return "Your reminders: " + ", ".join(lines)


def complete_reminder(reminder_id: int) -> str:
    reminders = load_reminders()
    for r in reminders:
        if r.get("id") == reminder_id:
            r["done"] = True
            save_reminders(reminders)
            return f"Marked reminder {reminder_id} as complete."
    return f"Reminder {reminder_id} not found."


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


# ============== WEATHER (Free API) ==============

def get_weather(city: str = "Singapore") -> str:
    """Get weather using wttr.in (free, no API key)"""
    try:
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data['current_condition'][0]
        temp_c = current['temp_C']
        desc = current['weatherDesc'][0]['value']
        humidity = current['humidity']
        
        return f"In {city}: {temp_c}°C, {desc}, humidity {humidity}%."
    except:
        return f"Couldn't get weather for {city}."


# ============== CONTROL COMMANDS ==============

def pause_listening() -> str:
    """Signal to pause voice listening"""
    return "__PAUSE__"


def resume_listening() -> str:
    """Signal to resume voice listening"""
    return "__RESUME__"


def exit_jarvis() -> str:
    """Signal to exit Jarvis"""
    return "__EXIT__"


# ============== NOTES ==============

def create_note(title: str, content: str = "") -> str:
    """Create a note in Apple Notes"""
    try:
        script = f'''
        tell application "Notes"
            make new note at folder "Notes" with properties {{name: "{title}", body:"{content}"}}
        end tell
        '''
        subprocess.run(["osascript", "-e", script], check=True, timeout=5)
        return f"Created note: {title}"
    except:
        return "Couldn't create note."


# ============== TOOL REGISTRY ==============

TOOLS = {
    # Search & Web
    "search_web": {
        "function": search_web,
        "description": "Search the web and get actual results to read aloud",
        "parameters": {"query": "what to search for"}
    },
    "open_website": {
        "function": open_website,
        "description": "Open a website in the browser",
        "parameters": {"url": "website URL"}
    },
    
    # Apps
    "open_app": {
        "function": open_app,
        "description": "Open an application",
        "parameters": {"app_name": "name of the app"}
    },
    
    # Time
    "get_time": {
        "function": get_time,
        "description": "Get current time and date",
        "parameters": {}
    },
    
    # Volume & System
    "set_volume": {
        "function": set_volume,
        "description": "Control system volume by percentage or action",
        "parameters": {"level": "0-100 (optional)", "action": "up/down/mute/unmute (optional)"}
    },
    "take_screenshot": {
        "function": take_screenshot,
        "description": "Take a screenshot",
        "parameters": {"filename": "optional filename"}
    },
    "get_battery": {
        "function": get_battery,
        "description": "Get battery status",
        "parameters": {}
    },
    "toggle_wifi": {
        "function": toggle_wifi,
        "description": "Turn WiFi on or off",
        "parameters": {"action": "on or off"}
    },
    
    # Reminders
    "add_reminder": {
        "function": add_reminder,
        "description": "Add a reminder",
        "parameters": {"text": "what to remember"}
    },
    "get_reminders": {
        "function": get_reminders,
        "description": "List all active reminders",
        "parameters": {}
    },
    "complete_reminder": {
        "function": complete_reminder,
        "description": "Mark a reminder as done",
        "parameters": {"reminder_id": "reminder number"}
    },
    "clear_reminders": {
        "function": clear_reminders,
        "description": "Clear all reminders",
        "parameters": {}
    },
    
    # Weather
    "get_weather": {
        "function": get_weather,
        "description": "Get current weather for a city",
        "parameters": {"city": "city name (default: Singapore)"}
    },
    
    # Notes
    "create_note": {
        "function": create_note,
        "description": "Create a note in Apple Notes",
        "parameters": {"title": "note title", "content": "note content (optional)"}
    },
    
    # Control
    "pause_listening": {
        "function": pause_listening,
        "description": "Stop listening temporarily (user says pause, stop, wait)",
        "parameters": {}
    },
    "exit_jarvis": {
        "function": exit_jarvis,
        "description": "Exit Jarvis (user says goodbye, quit, exit)",
        "parameters": {}
    },
}
