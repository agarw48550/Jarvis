from __future__ import annotations
import os
import datetime
from typing import Any, Dict, List, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/calendar.events",
]


def _get_creds() -> Credentials:
    creds: Optional[Credentials] = None
    # token.json stores the user's access and refresh tokens
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def list_events(max_results: int = 10) -> List[Dict[str, Any]]:
    creds = _get_creds()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.datetime.utcnow().isoformat() + "Z"  # 'Z' indicates UTC time
    events_result = (
        service.events()
        .list(calendarId="primary", timeMin=now, maxResults=max_results, singleEvents=True, orderBy="startTime")
        .execute()
    )
    events = events_result.get("items", [])
    simplified = []
    for e in events:
        start = e.get("start", {}).get("dateTime") or e.get("start", {}).get("date")
        simplified.append({
            "id": e.get("id"),
            "summary": e.get("summary", "(no title)"),
            "start": start,
        })
    return simplified


def create_event(summary: str, start_iso: str, end_iso: str, description: str | None = None, location: str | None = None) -> Dict[str, Any]:
    creds = _get_creds()
    service = build("calendar", "v3", credentials=creds)

    event_body: Dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    if description:
        event_body["description"] = description
    if location:
        event_body["location"] = location

    event = service.events().insert(calendarId="primary", body=event_body).execute()
    return {"id": event.get("id"), "htmlLink": event.get("htmlLink")}
