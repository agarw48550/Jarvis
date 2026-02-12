"""
Proactive "Nudge" Module
Part of the "Elephant" Protocol.
Tracks active goals and nudges the user if activity stalls or deadlines approach.
"""

import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime, timedelta

# Database path (reuse same DB)
DB_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DB_DIR / "jarvis.db"

class NudgeManager:
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
        self.running = False
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS active_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_text TEXT NOT NULL,
                deadline DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active', -- active, completed, abandoned
                last_nudge_at DATETIME
            )
        """)
        conn.commit()
        conn.close()

    def set_goal(self, text, deadline_minutes=None):
        """Set a new active goal."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        deadline = None
        if deadline_minutes:
            deadline = datetime.now() + timedelta(minutes=float(deadline_minutes))
            
        cursor.execute("""
            INSERT INTO active_goals (goal_text, deadline, status)
            VALUES (?, ?, 'active')
        """, (text, deadline))
        conn.commit()
        conn.close()
        print(f"🎯 Goal set: {text}")

    def complete_goal(self, text_snippet):
        """Mark a goal as complete."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE active_goals 
            SET status = 'completed' 
            WHERE status = 'active' AND goal_text LIKE ?
        """, (f"%{text_snippet}%",))
        conn.commit()
        conn.close()

    def check_goals(self):
        """Check for stale goals or approaching deadlines."""
        if not self.session_manager:
            return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Find active goals
        cursor.execute("SELECT id, goal_text, deadline, last_nudge_at FROM active_goals WHERE status = 'active'")
        goals = cursor.fetchall()
        
        now = datetime.now()
        
        for gid, text, deadline_str, last_nudge_str in goals:
            # Parse dates
            deadline = datetime.fromisoformat(deadline_str) if deadline_str else None
            last_nudge = datetime.fromisoformat(last_nudge_str) if last_nudge_str else None
            
            should_nudge = False
            
            # Logic: Nudge if deadline is close (within 5 mins) and haven't nudged recently
            if deadline and deadline > now:
                time_left = (deadline - now).total_seconds() / 60
                if time_left < 10 and (not last_nudge or (now - last_nudge).total_seconds() > 300):
                    should_nudge = True
                    message = f"Just a heads up, you wanted to {text} in about {int(time_left)} minutes."
            
            # Logic: If no deadline, but goal is old (> 1 hour) and no recent nudge
            # (Skipped for simplicity, sticking to deadline nudges first)

            if should_nudge:
                print(f"🔔 Nudging: {message}")
                self.session_manager.speak_async(message)
                
                # Update last nudge
                cursor.execute("UPDATE active_goals SET last_nudge_at = ? WHERE id = ?", (now, gid))
                conn.commit()

        conn.close()

    def start_loop(self):
        """Start background checking loop."""
        if self.running: 
            return
        self.running = True
        
        def _loop():
            while self.running:
                try:
                    self.check_goals()
                except Exception as e:
                    print(f"⚠️ Nudge loop error: {e}")
                time.sleep(60) # Check every minute
        
        t = threading.Thread(target=_loop, daemon=True)
        t.start()
