#!/usr/bin/env python3
"""
Jarvis v8 Actions - Complete Agentic Toolkit with Email & Calendar
"""

import os
import sys
import subprocess
import webbrowser
import json
import urllib.parse
import base64
from datetime import datetime, timedelta
from pathlib import Path
from email.mime.text import MIMEText

# ============== Constants ==============
REMINDERS_FILE = Path(__file__).parent / "reminders.json"
GOOGLE_CREDS_FILE = Path(__file__).parent / "credentials.json"
GOOGLE_TOKEN_FILE = Path(__file__).parent / "token.json"


# ============== WEB SEARCH (Smart with Summarization) ==============

def search_web(query: str) -> str:
    """Search the web and return summarized results"""
    try:
        # Try new package name first
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        
        if results:
            # Format for LLM to summarize later
            summaries = []
            for r in results[:5]:
                title = r.get('title', '')[:50]
                body = r.get('body', '')[:200]
                if title and body:
                    summaries.append(f"• {title}: {body}")
            
            if summaries:
                return "Search results:\n" + "\n".join(summaries)
        
        return f"No results found for '{query}'."
        
    except Exception as e:
        return f"Search error: {str(e)[:100]}"


def search_news(query: str) -> str:
    """Search for recent news"""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=3))
        
        if results:
            news = []
            for r in results[:3]:
                title = r.get('title', '')[:60]
                news.append(f"• {title}")
            return "Recent news:\n" + "\n".join(news)
        
        return f"No news found for '{query}'."
    except Exception as e:
        return f"News search error: {str(e)[:50]}"


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
        "excel": "Microsoft Excel", "zoom": "zoom.us", "teams": "Microsoft Teams",
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


def open_website(url: str) -> str:
    """Open a website"""
    if not url.startswith('http'):
        url = 'https://' + url
    webbrowser.open(url)
    return f"Opened {url}."


# ============== TIME & DATE ==============

def get_time() -> str:
    now = datetime.now()
    return f"It's {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d')}."


def set_timer(minutes: int, label: str = "Timer") -> str:
    """Set a timer (uses macOS notification)"""
    try:
        seconds = minutes * 60
        # Run timer in background
        script = f'''
        do shell script "sleep {seconds} && osascript -e 'display notification \\"{label} is done!\\\" with title \\\"Timer\\\"' && afplay /System/Library/Sounds/Glass.aiff" &
        '''
        subprocess.Popen(["osascript", "-e", script])
        return f"Timer set for {minutes} minutes."
    except:
        return "Couldn't set timer."


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
        }
        
        if action and action in actions:
            subprocess.run(["osascript", "-e", actions[action]], check=True, timeout=5)
            return f"Volume {action}."
        
        return "Specify level or action."
    except Exception as e:
        return f"Volume error: {e}"


def get_battery() -> str:
    """Get battery status"""
    try:
        import re
        result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
        match = re.search(r'(\d+)%', result.stdout)
        if match:
            percent = match.group(1)
            charging = "charging" if "charging" in result.stdout.lower() else "on battery"
            return f"Battery at {percent}%, {charging}."
    except:
        pass
    return "Battery info unavailable."


def take_screenshot() -> str:
    """Take a screenshot"""
    try:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.expanduser(f"~/Desktop/{filename}")
        subprocess.run(["screencapture", "-x", path], check=True, timeout=10)
        return f"Screenshot saved to Desktop."
    except:
        return "Couldn't take screenshot."


def control_music(action: str) -> str:
    """Control Music app playback"""
    try:
        if action == "play":
            subprocess.run(["osascript", "-e", 'tell application "Music" to play'])
        elif action == "pause":
            subprocess.run(["osascript", "-e", 'tell application "Music" to pause'])
        elif action == "next":
            subprocess.run(["osascript", "-e", 'tell application "Music" to next track'])
        elif action == "previous":
            subprocess.run(["osascript", "-e", 'tell application "Music" to previous track'])
        return f"Music {action}."
    except:
        return "Couldn't control music."


# ============== REMINDERS ==============

def add_reminder(text: str) -> str:
    reminders = load_reminders()
    reminders.append({
        "id": len(reminders) + 1,
        "text": text,
        "created": datetime.now().isoformat()
    })
    save_reminders(reminders)
    return f"Reminder added: {text}"


def get_reminders() -> str:
    reminders = load_reminders()
    if not reminders:
        return "You have no reminders."
    lines = [f"{i+1}. {r['text']}" for i, r in enumerate(reminders)]
    return "Your reminders: " + "; ".join(lines)


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


# ============== WEATHER ==============

def get_weather(city: str = "Singapore") -> str:
    """Get weather using wttr.in"""
    try:
        import requests
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data['current_condition'][0]
        temp = current['temp_C']
        desc = current['weatherDesc'][0]['value']
        humidity = current['humidity']
        
        return f"{city}: {temp}°C, {desc}, humidity {humidity}%."
    except:
        return f"Couldn't get weather for {city}."


# ============== CALCULATIONS ==============

def calculate(expression: str) -> str:
    """Evaluate a math expression safely"""
    try:
        # Only allow safe characters
        allowed = set('0123456789+-*/().% ')
        if all(c in allowed for c in expression):
            result = eval(expression)
            return f"The answer is {result}."
    except:
        pass
    return "Couldn't calculate that."


# ============== GMAIL (Requires OAuth Setup) ==============

def send_email(to: str, subject: str, body: str) -> str:
    """Send email via Gmail API"""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        creds = None
        
        if GOOGLE_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif GOOGLE_CREDS_FILE.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
                GOOGLE_TOKEN_FILE.write_text(creds.to_json())
            else:
                return "Gmail not set up. Need credentials.json file."
        
        service = build('gmail', 'v1', credentials=creds)
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"Email sent to {to}."
        
    except Exception as e:
        return f"Email error: {str(e)[:100]}"


# ============== GOOGLE CALENDAR (Requires OAuth Setup) ==============

def get_calendar_events(days: int = 1) -> str:
    """Get upcoming calendar events"""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = None
        
        if GOOGLE_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif GOOGLE_CREDS_FILE.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
                GOOGLE_TOKEN_FILE.write_text(creds.to_json())
            else:
                return "Calendar not set up. Need credentials.json file."
        
        service = build('calendar', 'v3', credentials=creds)
        
        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=days)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=end,
            maxResults=5, singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events."
        
        lines = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            summary = event.get('summary', 'Untitled')
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = dt.strftime('%I:%M %p')
                lines.append(f"• {time_str}: {summary}")
            except:
                lines.append(f"• {summary}")
        
        return "Your upcoming events: " + "; ".join(lines)
        
    except Exception as e:
        return f"Calendar error: {str(e)[:100]}"


def create_calendar_event(title: str, date: str = None, time: str = None, duration: int = 60) -> str:
    """Create a calendar event"""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from google.auth.transport.requests import Request
        
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        creds = None
        
        if GOOGLE_TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(GOOGLE_TOKEN_FILE), SCOPES)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif GOOGLE_CREDS_FILE.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(GOOGLE_CREDS_FILE), SCOPES)
                creds = flow.run_local_server(port=0)
                GOOGLE_TOKEN_FILE.write_text(creds.to_json())
            else:
                return "Calendar not set up."
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Default to tomorrow at 9am if no date/time specified
        start = datetime.now() + timedelta(days=1)
        start = start.replace(hour=9, minute=0, second=0)
        end = start + timedelta(minutes=duration)
        
        event = {
            'summary': title,
            'start': {'dateTime': start.isoformat(), 'timeZone': 'Asia/Singapore'},
            'end': {'dateTime': end.isoformat(), 'timeZone': 'Asia/Singapore'},
        }
        
        service.events().insert(calendarId='primary', body=event).execute()
        return f"Created event: {title}."
        
    except Exception as e:
        return f"Calendar error: {str(e)[:100]}"


# ============== CONTROL COMMANDS ==============

def pause_listening() -> str:
    return "__PAUSE__"


def exit_jarvis() -> str:
    return "__EXIT__"


# ============== TOOL REGISTRY ==============

TOOLS = {
    # Search
    "search_web": {
        "function": search_web,
        "description": "Search the web for any information",
        "parameters": {"query": "search query"}
    },
    "search_news": {
        "function": search_news,
        "description": "Search for recent news",
        "parameters": {"query": "news topic"}
    },
    
    # Apps
    "open_app": {
        "function": open_app,
        "description": "Open an application",
        "parameters": {"app_name": "app name"}
    },
    "open_website": {
        "function": open_website,
        "description": "Open a website in browser",
        "parameters": {"url": "website URL"}
    },
    
    # Time
    "get_time": {
        "function": get_time,
        "description": "Get current time and date",
        "parameters": {}
    },
    "set_timer": {
        "function": set_timer,
        "description": "Set a timer for X minutes",
        "parameters": {"minutes": "number of minutes", "label": "timer name (optional)"}
    },
    
    # System
    "set_volume": {
        "function": set_volume,
        "description": "Set volume level or action",
        "parameters": {"level": "0-100", "action": "up/down/mute/unmute"}
    },
    "get_battery": {
        "function": get_battery,
        "description": "Get battery status",
        "parameters": {}
    },
    "take_screenshot": {
        "function": take_screenshot,
        "description": "Take a screenshot",
        "parameters": {}
    },
    "control_music": {
        "function": control_music,
        "description": "Control Music app",
        "parameters": {"action": "play/pause/next/previous"}
    },
    
    # Reminders
    "add_reminder": {
        "function": add_reminder,
        "description": "Add a reminder",
        "parameters": {"text": "reminder text"}
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
    
    # Weather
    "get_weather": {
        "function": get_weather,
        "description": "Get weather for a city",
        "parameters": {"city": "city name"}
    },
    
    # Math
    "calculate": {
        "function": calculate,
        "description": "Do math calculation",
        "parameters": {"expression": "math expression like 5+3*2"}
    },
    
    # Email
    "send_email": {
        "function": send_email,
        "description": "Send an email via Gmail",
        "parameters": {"to": "recipient email", "subject": "email subject", "body": "email content"}
    },
    
    # Calendar
    "get_calendar_events": {
        "function": get_calendar_events,
        "description": "Get upcoming calendar events",
        "parameters": {"days": "number of days to look ahead (default 1)"}
    },
    "create_calendar_event": {
        "function": create_calendar_event,
        "description": "Create a calendar event",
        "parameters": {"title": "event title", "date": "date (optional)", "time": "time (optional)"}
    },
    
    # Control
    "pause_listening": {
        "function": pause_listening,
        "description": "Pause voice listening",
        "parameters": {}
    },
    "exit_jarvis": {
        "function": exit_jarvis,
        "description": "Exit/quit Jarvis",
        "parameters": {}
    },
}
