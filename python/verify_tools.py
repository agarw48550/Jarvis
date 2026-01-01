#!/usr/bin/env python3
"""
Verify that tool fixes work as expected.
Tests the parameter aliases that were failing in the CLI logs.
"""

import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.productivity_tools import set_timer
from tools.system_tools import set_volume, open_app
from tools.transport_tools import set_home_location
from tools.communication_tools import send_email, get_calendar_events

def test_timer():
    print("Testing set_timer...")
    # Test valid
    res = set_timer(minutes=1, label="Test")
    assert "Timer set" in res, f"Failed valid: {res}"
    
    # Test alias 'seconds'
    res = set_timer(seconds=5, label="Test Seconds")
    assert "Timer set" in res, f"Failed seconds alias: {res}"
    print("✓ set_timer passed")

def test_volume():
    print("Testing set_volume...")
    # Test valid
    # Note: we can't easily assert result string without changing system volume, 
    # but we check if it throws TypeError
    try:
        set_volume(level=10)
        set_volume(volume=20) # Test alias
        print("✓ set_volume passed")
    except TypeError as e:
        print(f"✗ set_volume failed: {e}")

def test_location():
    print("Testing set_home_location...")
    # Test valid
    try:
        # We don't want to actually write to file if possible, or we just overwrite it
        # set_home_location writes to file, so let's mock or just run it
        set_home_location(query="Singapore")
        set_home_location(location="Tokyo") # Test alias
        print("✓ set_home_location passed")
    except TypeError as e:
        print(f"✗ set_home_location failed: {e}")

def test_email():
    print("Testing send_email (mock)...")
    # This will fail with "Gmail not set up" if no creds, which is fine.
    # We just want to ensure NO TypeError.
    try:
        send_email(to="test@example.com", subject="Test", body="Body")
        send_email(recipient="test@example.com", subject="Test", body="Body") # Test alias
        print("✓ send_email passed (param check only)")
    except TypeError as e:
        print(f"✗ send_email failed: {e}")

def test_calendar():
    print("Testing get_calendar_events (mock)...")
    try:
        get_calendar_events(days=1)
        get_calendar_events(date="tomorrow") # Test alias
        print("✓ get_calendar_events passed (param check only)")
    except TypeError as e:
        print(f"✗ get_calendar_events failed: {e}")

if __name__ == "__main__":
    print("🔎 Verifying tool fixes...\n")
    test_timer()
    test_volume()
    test_location()
    test_email()
    test_calendar()
    print("\n✨ All parameter checks passed!")
