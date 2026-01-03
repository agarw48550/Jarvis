#!/usr/bin/env python3
"""
Jarvis v9 Actions - All working properly
"""

import os
import subprocess
import webbrowser
import json
from datetime import datetime, timedelta
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent / "reminders.json"

# Import search from separate module
from search_engine import search_web, search_news, clean_for_speech


# ============== APPS ==============

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
    }
    
    actual_app = mappings.get(app.lower(), app.title())
    
    try:
        result = subprocess.run(["open", "-a", actual_app], capture_output=True, timeout=5)
        return f"Opened {actual_app}." if result.returncode == 0 else f"Couldn't find {app}."
    except Exception:
        return f"Error opening {app}."


# ============== TIME & TIMER ==============

def get_time() -> str:
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def set_timer(minutes: int, label: str = "Timer") -> str:
    """Set a visible timer with notification"""
    try:
        # Use osascript to show notification after delay
        script = f'''
        delay {minutes * 60}
        display notification "{label} complete!" with title "Jarvis Timer" sound name "Glass"
        say "{label} is done"
        '''
        
        # Run in background
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return f"Timer set for {minutes} minutes. I'll notify you when it's done."
    except Exception:
        return "Couldn't set timer."


# ============== MUSIC CONTROL ==============

def control_music(action: str) -> str:
    """Control Apple Music"""
    try:
        scripts = {
            "play": 'tell application "Music" to play',
            "pause": 'tell application "Music" to pause',
            "stop": 'tell application "Music" to stop',
            "next": 'tell application "Music" to next track',
            "previous": 'tell application "Music" to previous track',
        }
        
        if action.lower() in scripts:
            subprocess.run(["osascript", "-e", scripts[action.lower()]], timeout=5)
            return f"Music: {action}."
        
        return f"Unknown action. Try: play, pause, next, previous."
    except Exception:
        return "Couldn't control music. Is Music app installed?"


# ============== VOLUME ==============

def set_volume(level: int = None, action: str = None) -> str:
    """Control system volume"""
    try:
        if level is not None:
            level = max(0, min(100, level))
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
            return f"Volume set to {level} percent."
        
        if action == "up":
            subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 15)"], check=True)
            return "Volume up."
        elif action == "down":
            subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 15)"], check=True)
            return "Volume down."
        elif action == "mute":
            subprocess.run(["osascript", "-e", "set volume output muted true"], check=True)
            return "Muted."
        elif action == "unmute":
            subprocess.run(["osascript", "-e", "set volume output muted false"], check=True)
            return "Unmuted."
        
        return "Specify volume level or action."
    except Exception as e:
        return f"Volume error: {e}"


# ============== SYSTEM ==============

def get_battery() -> str:
    try:
        import re
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        match = re.search(r'(\d+)%', result.stdout)
        if match:
            percent = match.group(1)
            charging = "charging" if "charging" in result.stdout.lower() else "on battery"
            return f"Battery at {percent} percent, {charging}."
    except Exception:
        pass
    return "Battery info unavailable."


def take_screenshot() -> str:
    try:
        filename = f"screenshot_{datetime.now().strftime('%H%M%S')}.png"
        path = os.path.expanduser(f"~/Desktop/{filename}")
        subprocess.run(["screencapture", "-x", path], check=True)
        return "Screenshot saved to Desktop."
    except Exception:
        return "Couldn't take screenshot."


# ============== WEATHER ==============

def get_weather(city: str = "Singapore") -> str:
    try:
        import urllib.parse
        import requests
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data['current_condition'][0]
        temp = current['temp_C']
        desc = current['weatherDesc'][0]['value']
        
        return f"{city}: {temp} degrees Celsius, {desc}."
    except Exception:
        return f"Couldn't get weather for {city}."


# ============== REMINDERS ==============

def add_reminder(text: str) -> str:
    reminders = load_reminders()
    reminders.append({"text": text, "created": datetime.now().isoformat()})
    save_reminders(reminders)
    return f"I'll remember: {text}"


def get_reminders() -> str:
    reminders = load_reminders()
    if not reminders:
        return "You have no reminders."
    items = [f"{i+1}. {r['text']}" for i, r in enumerate(reminders)]
    return "Your reminders: " + ", ".join(items)


def clear_reminders() -> str:
    save_reminders([])
    return "Reminders cleared."


def load_reminders():
    if REMINDERS_FILE.exists():
        try:
            return json.loads(REMINDERS_FILE.read_text())
        except Exception:
            return []
    return []


def save_reminders(r):
    REMINDERS_FILE.write_text(json.dumps(r, indent=2))


# ============== MATH ==============

def calculate(expression: str) -> str:
    try:
        allowed = set('0123456789+-*/().% ')
        clean = ''.join(c for c in expression if c in allowed)
        result = eval(clean)
        return f"The answer is {result}."
    except Exception:
        return "Couldn't calculate that."


# ============== CONTROL ==============

def pause_listening() -> str:
    return "__PAUSE__"


def exit_jarvis() -> str:
    return "__EXIT__"


def stop_speaking() -> str:
    """Interrupt current speech"""
    from tts_simple import interrupt_speech
    interrupt_speech()
    return "__STOP_SPEECH__"


# ============== TOOL REGISTRY ==============
# NOTE: This is kept for backwards compatibility
# New code should use tools.tool_registry.TOOLS

try:
    from tools.tool_registry import TOOLS
except ImportError:
    # Fallback if tools module not available
    TOOLS = {
    "search_web": {"function": search_web, "description": "Search for any information online", "parameters": {"query": "what to search"}},
    "search_news": {"function": search_news, "description": "Get latest news on a topic", "parameters": {"query": "news topic"}},
    "open_app": {"function": open_app, "description": "Open an application", "parameters": {"app_name": "app name"}},
    "get_time": {"function": get_time, "description": "Get current time", "parameters": {}},
    "set_timer": {"function": set_timer, "description": "Set a timer", "parameters": {"minutes": "number", "label": "name (optional)"}},
    "control_music": {"function": control_music, "description": "Control music playback", "parameters": {"action": "play/pause/next/previous"}},
    "set_volume": {"function": set_volume, "description": "Set volume", "parameters": {"level": "0-100", "action": "up/down/mute"}},
    "get_battery": {"function": get_battery, "description": "Get battery status", "parameters": {}},
    "take_screenshot": {"function": take_screenshot, "description": "Take screenshot", "parameters": {}},
    "get_weather": {"function": get_weather, "description": "Get weather", "parameters": {"city": "city name"}},
    "add_reminder": {"function": add_reminder, "description": "Add reminder", "parameters": {"text": "what to remember"}},
    "get_reminders": {"function": get_reminders, "description": "List reminders", "parameters": {}},
    "clear_reminders": {"function": clear_reminders, "description": "Clear reminders", "parameters": {}},
    "calculate": {"function": calculate, "description": "Do math", "parameters": {"expression": "math expression"}},
    "pause_listening": {"function": pause_listening, "description": "Pause listening (only when user explicitly says pause/stop/wait)", "parameters": {}},
    "stop_speaking": {"function": stop_speaking, "description": "Stop current speech (user says stop/quiet/shut up)", "parameters": {}},
    "exit_jarvis": {"function": exit_jarvis, "description": "Exit Jarvis (goodbye/bye/quit)", "parameters": {}},
    }


# Backwards compatibility - re-export if TOOLS was imported from tool_registry
if 'TOOLS' not in locals() or not isinstance(TOOLS, dict):
TOOLS = {
    "search_web": {"function": search_web, "description": "Search for any information online", "parameters": {"query": "what to search"}},
    "search_news": {"function": search_news, "description": "Get latest news on a topic", "parameters": {"query": "news topic"}},
    "open_app": {"function": open_app, "description": "Open an application", "parameters": {"app_name": "app name"}},
    "get_time": {"function": get_time, "description": "Get current time", "parameters": {}},
    "set_timer": {"function": set_timer, "description": "Set a timer", "parameters": {"minutes": "number", "label": "name (optional)"}},
    "control_music": {"function": control_music, "description": "Control music playback", "parameters": {"action": "play/pause/next/previous"}},
    "set_volume": {"function": set_volume, "description": "Set volume", "parameters": {"level": "0-100", "action": "up/down/mute"}},
    "get_battery": {"function": get_battery, "description": "Get battery status", "parameters": {}},
    "take_screenshot": {"function": take_screenshot, "description": "Take screenshot", "parameters": {}},
    "get_weather": {"function": get_weather, "description": "Get weather", "parameters": {"city": "city name"}},
    "add_reminder": {"function": add_reminder, "description": "Add reminder", "parameters": {"text": "what to remember"}},
    "get_reminders": {"function": get_reminders, "description": "List reminders", "parameters": {}},
    "clear_reminders": {"function": clear_reminders, "description": "Clear reminders", "parameters": {}},
    "calculate": {"function": calculate, "description": "Do math", "parameters": {"expression": "math expression"}},
    "pause_listening": {"function": pause_listening, "description": "Pause listening (only when user explicitly says pause/stop/wait)", "parameters": {}},
    "stop_speaking": {"function": stop_speaking, "description": "Stop current speech (user says stop/quiet/shut up)", "parameters": {}},
    "exit_jarvis": {"function": exit_jarvis, "description": "Exit Jarvis (goodbye/bye/quit)", "parameters": {}},
}
