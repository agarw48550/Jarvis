import base64
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from pathlib import Path
from googleapiclient.discovery import build
from google_auth import get_credentials

def get_service(name, version):
    creds = get_credentials()
    if not creds:
        return None
    return build(name, version, credentials=creds)

def send_email(to: str = None, recipient: str = None, subject: str = "No Subject", body: str = "Sent from Jarvis") -> str:
    """Send email via Gmail API"""
    try:
        target = to or recipient
        if not target:
            return "Please specify a recipient email address."

        service = get_service('gmail', 'v1')
        if not service:
            return "Gmail not set up. Run: python google_auth.py"
        
        message = MIMEText(body)
        message['to'] = target
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"Email sent to {target}."
        
    except Exception as e:
        return f"Email failed: {str(e)[:100]}"


def read_emails(count: int = 3) -> str:
    """Read recent emails"""
    try:
        service = get_service('gmail', 'v1')
        if not service:
            return "Gmail not set up. Run: python google_auth.py"
        
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
        return f"Email error: {str(e)[:100]}"


def get_calendar_events(days: int = 1, date: str = None) -> str:
    """Get upcoming calendar events"""
    try:
        service = get_service('calendar', 'v3')
        if not service:
            return "Calendar not set up. Run: python google_auth.py"
        
        # Determine duration
        search_days = days
        start_time = datetime.now(timezone.utc)
        
        if date:
            try:
                # Try to parse date if provided
                start_time = datetime.fromisoformat(date.replace('Z', '+00:00'))
            except ValueError:
                if 'today' in str(date).lower():
                    search_days = 1
                elif 'week' in str(date).lower():
                    search_days = 7
        
        now_str = start_time.isoformat()
        end_str = (start_time + timedelta(days=search_days)).isoformat()
        
        events_result = service.events().list(
            calendarId='primary', timeMin=now_str, timeMax=end_str,
            maxResults=10, singleEvents=True, orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        
        if not events:
            return "No upcoming events."
        
        summaries = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            title = event.get('summary', 'Untitled')[:30]
            try:
                dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                time_str = dt.strftime('%I:%M %p')
                summaries.append(f"{time_str}: {title}")
            except ValueError:
                summaries.append(title)
        
        return "Upcoming events: " + ", ".join(summaries)
        
    except Exception as e:
        return f"Calendar error: {str(e)[:100]}"


def create_calendar_event(title: str, date: str = None, time: str = None) -> str:
    """Create a calendar event"""
    try:
        service = get_service('calendar', 'v3')
        if not service:
            return "Calendar not set up. Run: python google_auth.py"
        
        # Parse date and time if provided
        start_time = datetime.now() + timedelta(days=1)
        if date:
            try:
                parsed_date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                start_time = start_time.replace(year=parsed_date.year, month=parsed_date.month, day=parsed_date.day)
            except ValueError:
                pass
        
        if time:
            try:
                parsed_time = datetime.strptime(time, '%H:%M')
                start_time = start_time.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0)
            except ValueError:
                try:
                    parsed_time = datetime.strptime(time, '%I:%M %p')
                    start_time = start_time.replace(hour=parsed_time.hour, minute=parsed_time.minute, second=0)
                except ValueError:
                    pass
        elif not date:
            # Default to tomorrow at 9am if absolutely nothing provided
            start_time = start_time.replace(hour=9, minute=0, second=0)
            
        end_time = start_time + timedelta(hours=1)
        
        event = {
            'summary': title,
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Singapore'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Singapore'},
        }
        
        service.events().insert(calendarId='primary', body=event).execute()
        return f"Created event: {title} on {start_time.strftime('%Y-%m-%d %I:%M %p')}"
        
    except Exception as e:
        return f"Calendar error: {str(e)[:100]}"
