"""
Notification Tools for Jarvis
Reads and summarizes macOS notifications using AppleScript.
"""

import subprocess
import json
import os


def get_recent_notifications(count: str = "10") -> str:
    """Get recent macOS notifications using AppleScript.
    
    Args:
        count: Number of recent notifications to retrieve (as string for tool compatibility)
    Returns:
        Formatted string of recent notifications
    """
    count = int(count) if isinstance(count, str) else count
    
    # AppleScript to get notifications from Notification Center
    script = '''
    tell application "System Events"
        set notifList to {}
        try
            -- Get notifications from Notification Center
            tell process "NotificationCenter"
                set notifWindows to every window
                repeat with w in notifWindows
                    try
                        set notifTitle to name of w
                        set end of notifList to notifTitle
                    end try
                end repeat
            end tell
        end try
        
        -- Also check for banner notifications
        try
            set bannerNotifs to do shell script "sqlite3 $(getconf DARWIN_USER_DIR)com.apple.notificationcenter/db2/db 'SELECT app_id, substr(data,1,200) FROM record ORDER BY delivered_date DESC LIMIT " & PLACEHOLDER_COUNT & "' 2>/dev/null || echo 'no_access'"
            if bannerNotifs is not "no_access" then
                return bannerNotifs
            end if
        end try
        
        return notifList as text
    end tell
    '''
    script = script.replace("PLACEHOLDER_COUNT", str(count))
    
    try:
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return f"📬 Recent Notifications:\n{result.stdout.strip()}"
        
        # Fallback: check notification center database directly
        return _read_notification_db(count)
        
    except subprocess.TimeoutExpired:
        return "⚠️ Timed out reading notifications."
    except Exception as e:
        return f"⚠️ Could not read notifications: {e}"


def _read_notification_db(count: int) -> str:
    """Fallback: Read notification database directly."""
    try:
        darwin_user_dir = subprocess.run(
            ['getconf', 'DARWIN_USER_DIR'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        
        db_path = os.path.join(darwin_user_dir, 'com.apple.notificationcenter', 'db2', 'db')
        
        if not os.path.exists(db_path):
            return "📭 No notification database found. macOS might require Full Disk Access permission."
        
        import sqlite3
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT app_id, delivered_date, data 
                FROM record 
                ORDER BY delivered_date DESC 
                LIMIT ?
            """, (count,))
            
            rows = cursor.fetchall()
            if not rows:
                return "📭 No recent notifications found."
            
            lines = ["📬 Recent Notifications:"]
            for app_id, date, data in rows:
                app_name = app_id.split('.')[-1] if app_id else "Unknown"
                # Try to extract title from plist data
                title = _extract_notification_title(data) if data else "Notification"
                lines.append(f"  • [{app_name}] {title}")
            
            return "\n".join(lines)
            
        finally:
            conn.close()
            
    except Exception as e:
        return f"📭 Could not read notification database: {e}. Try granting Full Disk Access in System Settings > Privacy & Security."


def _extract_notification_title(data):
    """Try to extract a notification title from the binary plist data."""
    try:
        import plistlib
        plist = plistlib.loads(data)
        # Common key paths in notification plists
        for key in ['titl', 'subt', 'body', 'req']:
            if key in plist:
                val = plist[key]
                if isinstance(val, dict):
                    return str(val.get('loc', val))
                return str(val)
        return str(plist)[:100]
    except Exception:
        return "Notification"


def summarize_notifications() -> str:
    """Get recent notifications and provide a summary.
    
    Returns:
        AI-generated summary of recent notifications
    """
    notifs = get_recent_notifications("20")
    
    if "No recent notifications" in notifs or "Could not read" in notifs:
        return notifs
    
    try:
        # Use Groq for fast summarization
        from groq import Groq
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Summarize these notifications concisely. Group by app. Highlight anything urgent."},
                {"role": "user", "content": notifs}
            ],
            max_tokens=300
        )
        return f"📋 Notification Summary:\n{response.choices[0].message.content}"
    except Exception as e:
        # Fallback: just return raw notifications
        return f"{notifs}\n\n(Could not generate summary: {e})"


def get_notification_count() -> str:
    """Get count of recent notifications.
    
    Returns:
        Count of recent notifications
    """
    try:
        darwin_user_dir = subprocess.run(
            ['getconf', 'DARWIN_USER_DIR'],
            capture_output=True, text=True, timeout=5
        ).stdout.strip()
        
        db_path = os.path.join(darwin_user_dir, 'com.apple.notificationcenter', 'db2', 'db')
        
        if not os.path.exists(db_path):
            return "Could not access notification database."
        
        import sqlite3
        conn = sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT COUNT(*) FROM record")
            total = cursor.fetchone()[0]
            
            # Count from last 24 hours
            cursor.execute("""
                SELECT COUNT(*) FROM record 
                WHERE delivered_date > (strftime('%s','now') - 86400)
            """)
            recent = cursor.fetchone()[0]
            
            return f"📬 You have {total} total notifications, {recent} in the last 24 hours."
        finally:
            conn.close()
            
    except Exception as e:
        return f"Could not count notifications: {e}"
