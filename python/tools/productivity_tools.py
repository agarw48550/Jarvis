#!/usr/bin/env python3
"""Productivity tools - Calendar, reminders, timers"""

import subprocess
import json
from datetime import datetime
from pathlib import Path

REMINDERS_FILE = Path(__file__).parent.parent / "reminders.json"


def get_time() -> str:
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def set_timer(minutes: int = None, seconds: int = None, duration: int = None, label: str = "Timer") -> str:
    """Set a visible timer with notification"""
    try:
        # Handle aliases
        mins = minutes if minutes is not None else 0
        secs = seconds if seconds is not None else 0
        
        # Determine total duration
        total_seconds = (mins * 60) + secs
        
        # If no time set, default to 5 minutes
        if total_seconds == 0:
            if duration:
                total_seconds = duration * 60 # Assume minutes for generic duration
            else:
                total_seconds = 300
        
        display_mins = total_seconds / 60
        
        script = f'''
        delay {total_seconds}
        display notification "{label} complete!" with title "Jarvis Timer" sound name "Glass"
        say "{label} is done"
        '''
        
        subprocess.Popen(
            ["osascript", "-e", script],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        return f"Timer set for {minutes} minutes. I'll notify you when it's done."
    except:
        return "Couldn't set timer."


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
        except:
            return []
    return []


def save_reminders(r):
    REMINDERS_FILE.write_text(json.dumps(r, indent=2))
