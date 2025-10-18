from datetime import datetime
import pytz
import os

def now() -> str:
    tz = os.getenv("TIMEZONE")
    if tz:
        try:
            dt = datetime.now(pytz.timezone(tz))
        except Exception:
            dt = datetime.now()
    else:
        dt = datetime.now()
    return dt.strftime("%A, %B %d, %Y %I:%M %p")
