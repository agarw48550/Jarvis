"""
Jarvis Scheduler — Lightweight cron-like task scheduler.
Stores tasks in SQLite and fires them from a background thread.
"""

import sqlite3
import threading
import time
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


DB_PATH = Path(__file__).parent.parent / "data" / "scheduler.db"


class CronScheduler:
    """Simple scheduler that checks for due tasks every 30 seconds."""
    
    def __init__(self, on_speak=None):
        """
        Args:
            on_speak: Callback function that takes a string and speaks it aloud.
                      If None, reminders are just printed.
        """
        self.on_speak = on_speak
        self.running = False
        self.thread = None
        self._init_db()
    
    def _init_db(self):
        """Create the scheduled_tasks table if it doesn't exist."""
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                action_type TEXT NOT NULL DEFAULT 'remind',
                action_data TEXT,
                next_run TEXT NOT NULL,
                recurrence TEXT,
                enabled INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.commit()
        conn.close()
    
    def add_task(self, description: str, run_at: str, action_type: str = "remind",
                 action_data: str = None, recurrence: str = None) -> int:
        """
        Schedule a new task.
        
        Args:
            description: What the task is about
            run_at: ISO format datetime string (e.g., "2026-02-12T15:00:00")
            action_type: "remind" (speak), "notify" (macOS notification), "run_tool" (execute tool)
            action_data: Tool name or extra data for the action
            recurrence: "daily", "hourly", "weekly", or None for one-time
        
        Returns:
            Task ID
        """
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO scheduled_tasks (description, action_type, action_data, next_run, recurrence) VALUES (?, ?, ?, ?, ?)",
            (description, action_type, action_data, run_at, recurrence)
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return task_id
    
    def list_tasks(self) -> list:
        """List all active scheduled tasks."""
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, description, action_type, next_run, recurrence, enabled FROM scheduled_tasks WHERE enabled = 1 ORDER BY next_run"
        )
        tasks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return tasks
    
    def cancel_task(self, task_id: int) -> bool:
        """Cancel (disable) a scheduled task."""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("UPDATE scheduled_tasks SET enabled = 0 WHERE id = ?", (task_id,))
        changed = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return changed
    
    def start(self):
        """Start the background scheduler thread."""
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        print("⏰ [SCHEDULER] Started background scheduler.")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        print("⏰ [SCHEDULER] Stopped.")
    
    def _run_loop(self):
        """Main scheduler loop — checks for due tasks every 30 seconds."""
        while self.running:
            try:
                self._check_due_tasks()
            except Exception as e:
                print(f"⚠️ [SCHEDULER] Error: {e}")
            time.sleep(30)
    
    def _check_due_tasks(self):
        """Check and execute any due tasks."""
        now = datetime.now().isoformat()
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM scheduled_tasks WHERE enabled = 1 AND next_run <= ?",
            (now,)
        )
        
        due_tasks = cursor.fetchall()
        
        for task in due_tasks:
            try:
                self._execute_task(dict(task))
            except Exception as e:
                print(f"⚠️ [SCHEDULER] Failed to execute task {task['id']}: {e}")
            
            # Handle recurrence or disable one-time tasks
            if task['recurrence']:
                next_run = self._calculate_next_run(task['next_run'], task['recurrence'])
                cursor.execute(
                    "UPDATE scheduled_tasks SET next_run = ? WHERE id = ?",
                    (next_run, task['id'])
                )
            else:
                cursor.execute(
                    "UPDATE scheduled_tasks SET enabled = 0 WHERE id = ?",
                    (task['id'],)
                )
        
        conn.commit()
        conn.close()
    
    def _execute_task(self, task: dict):
        """Execute a due task based on its type."""
        action = task['action_type']
        desc = task['description']
        
        print(f"⏰ [SCHEDULER] Firing task #{task['id']}: {desc}")
        
        if action == "remind":
            # Speak the reminder aloud
            message = f"Reminder: {desc}"
            if self.on_speak:
                self.on_speak(message)
            else:
                print(f"🔔 {message}")
            # Also send macOS notification as backup
            self._send_macos_notification("Jarvis Reminder", desc)
        
        elif action == "notify":
            self._send_macos_notification("Jarvis", desc)
        
        elif action == "run_tool":
            tool_name = task.get('action_data', '')
            print(f"⚙️ [SCHEDULER] Would execute tool: {tool_name}")
            # Tool execution would be injected by the session manager
    
    def _send_macos_notification(self, title: str, message: str):
        """Send a native macOS notification."""
        try:
            script = f'display notification "{message}" with title "{title}"'
            subprocess.run(
                ['osascript', '-e', script],
                capture_output=True, timeout=5
            )
        except Exception as e:
            print(f"⚠️ Notification failed: {e}")
    
    def _calculate_next_run(self, current: str, recurrence: str) -> str:
        """Calculate the next run time based on recurrence."""
        try:
            dt = datetime.fromisoformat(current)
        except ValueError:
            dt = datetime.now()
        
        if recurrence == "hourly":
            dt += timedelta(hours=1)
        elif recurrence == "daily":
            dt += timedelta(days=1)
        elif recurrence == "weekly":
            dt += timedelta(weeks=1)
        else:
            dt += timedelta(days=1)  # Default to daily
        
        return dt.isoformat()


# Singleton instance
_scheduler = None

def get_scheduler() -> CronScheduler:
    """Get or create the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
        _scheduler.start()
    return _scheduler
