#!/usr/bin/env python3
"""System tools - Apps, volume, battery, screenshots"""

import os
import re
import subprocess
from datetime import datetime
from typing import Optional


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value and str(value).strip():
            return str(value).strip()
    return None


def open_app(app_name: str = None, app: str = None, application: str = None) -> str:
    """Open application on macOS (accepts multiple parameter names)"""
    target = _first_non_empty(app_name, app, application)
    if not target:
        return "Tell me which app to open."
    app_clean = target.rstrip('.')
    
    mappings = {
        "safari": "Safari", "chrome": "Google Chrome", "firefox": "Firefox",
        "notes": "Notes", "notion": "Notion", "spotify": "Spotify",
        "slack": "Slack", "discord": "Discord", "terminal": "Terminal",
        "finder": "Finder", "messages": "Messages", "mail": "Mail",
        "calendar": "Calendar", "music": "Music", "photos": "Photos",
        "settings": "System Settings", "vscode": "Visual Studio Code",
    }
    
    actual_app = mappings.get(app_clean.lower(), app_clean.title())
    
    try:
        result = subprocess.run(["open", "-a", actual_app], capture_output=True, timeout=5)
        return f"Opened {actual_app}." if result.returncode == 0 else f"Couldn't find {app_clean}."
    except Exception:
        return f"Error opening {app_clean}."


def _coerce_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (ValueError, TypeError):
        return None


def set_volume(level: int = None, volume: int = None, action: str = None, percent: str = None, amount: str = None) -> str:
    """Control system volume"""
    desired_level = level if level is not None else None
    
    # Aliases
    if desired_level is None and volume is not None:
        try:
            desired_level = int(str(volume).replace('%', '').strip())
        except Exception:
            pass
            
    if desired_level is None:
        desired_level = _coerce_int(percent)
    if desired_level is None:
        desired_level = _coerce_int(amount)
        
    if desired_level is not None:
        level = max(0, min(100, desired_level))
    effective_action = action or (_first_non_empty(percent, amount) if desired_level is None else None)
    try:
        if level is not None:
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"], check=True)
            return f"Volume set to {level} percent."
        
        if effective_action == "up":
            subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 15)"], check=True)
            return "Volume up."
        elif effective_action == "down":
            subprocess.run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 15)"], check=True)
            return "Volume down."
        elif effective_action == "mute":
            subprocess.run(["osascript", "-e", "set volume output muted true"], check=True)
            return "Muted."
        elif effective_action == "unmute":
            subprocess.run(["osascript", "-e", "set volume output muted false"], check=True)
            return "Unmuted."
        
        return "Specify volume level or action."
    except Exception as e:
        return f"Volume error: {e}"


def get_battery() -> str:
    try:
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        stdout = result.stdout.lower()
        percent_match = re.search(r'(\d+)%', stdout)
        status = "on battery"
        if "charging" in stdout or "ac power" in stdout:
            status = "charging"
        elif "finishing charge" in stdout:
            status = "finishing charge"
        elif "discharging" in stdout or "battery power" in stdout:
            status = "on battery"
        if percent_match:
            percent = percent_match.group(1)
            return f"Battery at {percent} percent, {status}."
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


def set_brightness(level: int = None, amount: str = None) -> str:
    """Set screen brightness (0-100)"""
    if level is None and amount is not None:
        level = _coerce_int(amount)
    if level is None:
        return "Please specify a brightness level (0-100)."
    level = max(0, min(100, level))
    val = level / 100.0
    try:
        try:
             subprocess.run(["brightness", "-l"], capture_output=True, check=True)
             subprocess.run(["brightness", str(val)], check=True)
             return f"Brightness set to {level}%."
        except FileNotFoundError:
             return "I need the 'brightness' tool installed. Run: brew install brightness"
        except subprocess.CalledProcessError:
             pass
        return "I can't control brightness natively yet. Please install 'brew install brightness'."
    except Exception as e:
        return f"Error setting brightness: {e}"

def control_media(action: str) -> str:
    """Control system media playback: play, pause, next, previous"""
    action = action.lower().strip()
    
    # Define mapping for AppleScript commands
    # We target both Music and Spotify as they are the most common.
    # Generic media keys via System Events key codes is another option but app-specific is more reliable.
    
    scripts = {
        "play": [
            'tell application "Music" to play',
            'tell application "Spotify" to play'
        ],
        "pause": [
            'tell application "Music" to pause',
            'tell application "Spotify" to pause'
        ],
        "next": [
            'tell application "Music" to next track',
            'tell application "Spotify" to next track'
        ],
        "previous": [
            'tell application "Music" to previous track',
            'tell application "Spotify" to previous track'
        ],
        "toggle": [
            'tell application "Music" to playpause',
            'tell application "Spotify" to playpause'
        ]
    }
    
    if action == "stop": action = "pause"
    if action == "resume": action = "play"
    if action not in scripts and "play" in action and "pause" in action: action = "toggle"
    if action not in scripts:
        return f"Unsupported media action: {action}. Try: play, pause, next, previous."

    tried_apps = []
    for script in scripts[action]:
        app_name = "Music" if "Music" in script else "Spotify"
        try:
            # Check if app is running first to avoid launching it just to pause
            check_running = f'application "{app_name}" is running'
            is_running = subprocess.run(["osascript", "-e", check_running], capture_output=True, text=True).stdout.strip()
            
            if is_running == "true":
                subprocess.run(["osascript", "-e", script], check=True)
                tried_apps.append(app_name)
        except Exception:
            continue
            
    if tried_apps:
        return f"Media {action} executed on: {', '.join(tried_apps)}."
    
    # Generic fallback: System Events key codes for media (may require permissions)
    # F7: 98 (Prev), F8: 100 (Play/Pause), F9: 101 (Next)
    generic_codes = {
        "play": 100, "pause": 100, "toggle": 100,
        "next": 101, "previous": 98
    }
    
    try:
        code = generic_codes.get(action)
        if code:
            subprocess.run(["osascript", "-e", f'tell application "System Events" to key code {code}'], check=True)
            return f"Performed {action} via system media keys."
    except Exception:
        pass

    return "No active media players found (checked Music and Spotify)."
