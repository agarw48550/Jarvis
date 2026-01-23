#!/usr/bin/env python3
"""
Google OAuth setup for Gmail and Calendar
Run this once to authenticate, then tokens are saved
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    # Gmail
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    # Calendar
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    # Drive
    'https://www.googleapis.com/auth/drive.readonly',
    # Classroom
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly',
    # People (Contacts)
    'https://www.googleapis.com/auth/contacts.readonly',
    # Assistant
    'https://www.googleapis.com/auth/assistant-sdk-prototype',
]

TOKEN_FILE = Path(__file__).parent / "google_token.json"
CREDS_FILE = Path(__file__).parent / "google_credentials.json"


def create_credentials_file():
    """Create credentials.json from environment variables"""
    client_id = os.getenv("GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "")
    
    if not client_id or not client_secret:
        print("❌ Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET in .env")
        return False
    
    creds_data = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    CREDS_FILE.write_text(json.dumps(creds_data, indent=2))
    print(f"✅ Created {CREDS_FILE}")
    return True


def authenticate():
    """Run OAuth flow and save tokens"""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError
    except ImportError:
        print("❌ Install: pip install google-auth-oauthlib google-api-python-client")
        return None
    
    creds = None
    
    # Check for existing token
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    
    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"⚠️ Token refresh failed ({e}); removing old token and starting fresh auth.")
                try:
                    TOKEN_FILE.unlink(missing_ok=True)
                except Exception:
                    pass
                creds = None
        if not creds or not creds.valid:
            # Create credentials file if needed
            if not CREDS_FILE.exists():
                if not create_credentials_file():
                    return None
            
            print("\n" + "="*50)
            print("🔐 Google Authentication Required")
            print("="*50)
            print("A browser window will open for you to log in.")
            print("After logging in, you can close the browser.")
            print("="*50 + "\n")
            
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save token
        TOKEN_FILE.write_text(creds.to_json())
        print(f"✅ Token saved to {TOKEN_FILE}")
    
    return creds


def get_credentials():
    """Get credentials, authenticate if needed"""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            if creds and creds.valid:
                return creds
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json())
                return creds
    except Exception:
        pass
    
    return None


def is_authenticated() -> bool:
    """Check if we have valid credentials"""
    return get_credentials() is not None


if __name__ == "__main__":
    print("🔐 Google OAuth Setup for Jarvis\n")
    creds = authenticate()
    if creds:
        print("\n✅ Authentication successful!")
        print("You can now use Gmail and Calendar features.")
    else:
        print("\n❌ Authentication failed.")
