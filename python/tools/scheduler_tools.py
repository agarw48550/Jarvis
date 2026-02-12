"""
Scheduler Tools for Jarvis
Tools for scheduling reminders and recurring tasks.
"""

from datetime import datetime, timedelta
import re


def schedule_task(description: str, time_spec: str, recurrence: str = "") -> str:
    """Schedule a reminder or task.
    
    Args:
        description: What to remind about (e.g., "Take a break")
        time_spec: When to fire — accepts:
            - Relative: "in 5 minutes", "in 2 hours", "in 1 day"
            - Absolute: "at 3:00 PM", "at 15:00"
            - ISO: "2026-02-12T15:00:00"
        recurrence: Optional. "daily", "hourly", "weekly", or empty for one-time.
    
    Returns:
        Confirmation message with task ID
    """
    from core.scheduler import get_scheduler
    
    run_at = _parse_time(time_spec)
    if not run_at:
        return f"⚠️ Could not understand time '{time_spec}'. Try 'in 5 minutes', 'at 3:00 PM', or ISO format."
    
    recurrence = recurrence.strip().lower() if recurrence else None
    if recurrence and recurrence not in ("daily", "hourly", "weekly"):
        recurrence = None
    
    scheduler = get_scheduler()
    task_id = scheduler.add_task(
        description=description,
        run_at=run_at,
        action_type="remind",
        recurrence=recurrence
    )
    
    recur_text = f" (repeats {recurrence})" if recurrence else ""
    time_display = datetime.fromisoformat(run_at).strftime("%I:%M %p on %b %d")
    return f"✅ Scheduled: '{description}' at {time_display}{recur_text} (ID: {task_id})"


def list_scheduled_tasks() -> str:
    """List all active scheduled tasks.
    
    Returns:
        Formatted list of scheduled tasks
    """
    from core.scheduler import get_scheduler
    
    scheduler = get_scheduler()
    tasks = scheduler.list_tasks()
    
    if not tasks:
        return "📋 No active scheduled tasks."
    
    lines = ["📋 Scheduled Tasks:"]
    for t in tasks:
        time_display = datetime.fromisoformat(t['next_run']).strftime("%I:%M %p, %b %d")
        recur = f" (repeats {t['recurrence']})" if t.get('recurrence') else ""
        lines.append(f"  #{t['id']} — {t['description']} → {time_display}{recur}")
    
    return "\n".join(lines)


def cancel_scheduled_task(task_id: str) -> str:
    """Cancel a scheduled task by its ID.
    
    Args:
        task_id: The ID of the task to cancel
    
    Returns:
        Confirmation or error message
    """
    from core.scheduler import get_scheduler
    
    try:
        tid = int(task_id)
    except ValueError:
        return f"⚠️ Invalid task ID: {task_id}"
    
    scheduler = get_scheduler()
    if scheduler.cancel_task(tid):
        return f"✅ Cancelled task #{tid}."
    else:
        return f"⚠️ Task #{tid} not found or already cancelled."


def _parse_time(time_spec: str) -> str:
    """Parse a human-friendly time specification into ISO format."""
    time_spec = time_spec.strip().lower()
    now = datetime.now()
    
    # Relative: "in X minutes/hours/days"
    rel_match = re.match(r'in\s+(\d+)\s+(minute|min|hour|hr|day|second|sec)s?', time_spec)
    if rel_match:
        amount = int(rel_match.group(1))
        unit = rel_match.group(2)
        if unit in ('minute', 'min'):
            dt = now + timedelta(minutes=amount)
        elif unit in ('hour', 'hr'):
            dt = now + timedelta(hours=amount)
        elif unit in ('day',):
            dt = now + timedelta(days=amount)
        elif unit in ('second', 'sec'):
            dt = now + timedelta(seconds=amount)
        else:
            return None
        return dt.isoformat()
    
    # Absolute: "at HH:MM AM/PM" or "at HH:MM"
    at_match = re.match(r'at\s+(\d{1,2}):(\d{2})\s*(am|pm)?', time_spec)
    if at_match:
        hour = int(at_match.group(1))
        minute = int(at_match.group(2))
        ampm = at_match.group(3)
        
        if ampm == 'pm' and hour < 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt <= now:
            dt += timedelta(days=1)  # Schedule for tomorrow if time already passed
        return dt.isoformat()
    
    # ISO format: "2026-02-12T15:00:00"
    try:
        dt = datetime.fromisoformat(time_spec)
        return dt.isoformat()
    except ValueError:
        pass
    
    # "tomorrow at HH:MM"
    tmr_match = re.match(r'tomorrow\s+at\s+(\d{1,2}):(\d{2})\s*(am|pm)?', time_spec)
    if tmr_match:
        hour = int(tmr_match.group(1))
        minute = int(tmr_match.group(2))
        ampm = tmr_match.group(3)
        
        if ampm == 'pm' and hour < 12:
            hour += 12
        elif ampm == 'am' and hour == 12:
            hour = 0
        
        dt = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        return dt.isoformat()
    
    return None
