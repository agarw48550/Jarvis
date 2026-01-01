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
    except:
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
        except:
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
    except:
        pass
    return "Battery info unavailable."


def take_screenshot() -> str:
    try:
        filename = f"screenshot_{datetime.now().strftime('%H%M%S')}.png"
        path = os.path.expanduser(f"~/Desktop/{filename}")
        subprocess.run(["screencapture", "-x", path], check=True)
        return "Screenshot saved to Desktop."
    except:
        return "Couldn't take screenshot."
