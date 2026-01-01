#!/usr/bin/env python3
"""Communication tools - Gmail, Calendar"""

import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
import sys
from pathlib import Path

# Add parent directory to path to allow importing google_auth
sys.path.insert(0, str(Path(__file__).parent.parent))

def send_email(to: str = None, recipient: str = None, subject: str = "No Subject", body: str = "Sent from Jarvis") -> str:
    """Send email via Gmail API"""
    try:
        target = to or recipient
        if not target:
            return "Please specify a recipient email address."

        from google_auth import get_credentials
        from googleapiclient.discovery import build
        
        creds = get_credentials()
        if not creds:
            return "Gmail not set up. Run: python google_auth.py"
        
        service = build('gmail', 'v1', credentials=creds)
        
        message = MIMEText(body)
        message['to'] = target
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"Email sent to {target}."
        
    except Exception as e:
        return f"Email failed: {str(e)[:50]}"


def read_emails(count: int = 3) -> str:
    """Read recent emails"""
    try:
        from google_auth import get_credentials
        from googleapiclient.discovery import build
        
        creds = get_credentials()
        if not creds:
            return "Gmail not set up. Run: python google_auth.py"
        
        service = build('gmail', 'v1', credentials=creds)
        
        results = service.users().messages().list(userId='me', maxResults=count, labelIds=['INBOX']).execute()
        messages = results.get('messages', [])
        
        if not messages:
            return "No recent emails."
        
        summaries = []
        for msg in messages[:count]:
            msg_data = service.users().messages().get(userId='me', id=msg['id'], format='metadata').execute()
            headers = {h['name']: h['value'] for h in msg_data['payload']['headers']}
            sender = headers.get('From', 'Unknown')[:30]
            subject = headers.get('Subject', 'No subject')[:40]
            summaries.append(f"From {sender}: {subject}")
        
        return "Recent emails: " + ". ".join(summaries)
        
    except Exception as e:
        return f"Email error: {str(e)[:50]}"


def get_calendar_events(days: int = 1, date: str = None) -> str:
    """Get upcoming calendar events"""
    try:
        from google_auth import get_credentials
        from googleapiclient.discovery import build
        
        creds = get_credentials()
        if not creds:
            return "Calendar not set up. Run: python google_auth.py"
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Determine duration
        search_days = days
        if date and 'today' in str(date).lower():
            search_days = 1
        elif date and 'week' in str(date).lower():
            search_days = 7
        
        now = datetime.utcnow().isoformat() + 'Z'
        end = (datetime.utcnow() + timedelta(days=search_days)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now, timeMax=end,
            maxResults=5, singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events."
        
        summaries = []
        for event in events[:3]:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', 'Untitled')[:30]
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = dt.strftime('%I:%M %p')
                summaries.append(f"{time_str}: {title}")
            except:
                summaries.append(title)
        
        return "Upcoming events: " + ", ".join(summaries)
        
    except Exception as e:
        return f"Calendar error: {str(e)[:50]}"


def create_calendar_event(title: str, date: str = None, time: str = None) -> str:
    """Create a calendar event"""
    try:
        from google_auth import get_credentials
        from googleapiclient.discovery import build
        
        creds = get_credentials()
        if not creds:
            return "Calendar not set up. Run: python google_auth.py"
        
        service = build('calendar', 'v3', credentials=creds)
        
        # Default to tomorrow at 9am
        start = datetime.now().replace(hour=9, minute=0, second=0) + timedelta(days=1)
        end = start + timedelta(hours=1)
        
        event = {
            'summary': title,
            'start': {'dateTime': start.isoformat(), 'timeZone': 'Asia/Singapore'},
            'end': {'dateTime': end.isoformat(), 'timeZone': 'Asia/Singapore'},
        }
        
        service.events().insert(calendarId='primary', body=event).execute()
        return f"Created event: {title}"
        
    except Exception as e:
        return f"Calendar error: {str(e)[:50]}"
