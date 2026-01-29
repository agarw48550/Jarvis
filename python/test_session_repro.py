#!/usr/bin/env python3
"""Minimal repro: start JarvisSession directly to trigger session loop and capture debug logs."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from core.session_manager import JarvisSession

def main():
    s = JarvisSession()
    print("Starting session (simulating Force Wake)...")
    s.start()
    
    # Simulate a hang by doing nothing for 30 seconds
    # The watchdog should trigger at 25s and close the session
    print("Waiting 35s to test watchdog (Watchdog should kill at 25s)...")
    
    # We need to manually set status to PROCESSING to trigger watchdog
    # Normally this happens when a tool call or prompt is active
    time.sleep(2)
    s.state["status"] = "PROCESSING" 
    print("Set status to PROCESSING. Watchdog timer starts now.")
    
    start_wait = time.time()
    while s.state["active"]:
        time.sleep(1)
        if time.time() - start_wait > 35:
            print("❌ Watchdog failed to kill session.")
            break
            
    if not s.state["active"]:
        print("✅ Watchdog successfully killed session.")
    
    print("Stopping...")
    s.stop()
    time.sleep(2)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
