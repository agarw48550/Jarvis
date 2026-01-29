"""
Minimal NDJSON debug logger for agent instrumentation.
Writes to .cursor/debug.log. No deps beyond stdlib.
"""
import json
import time
from typing import Any, Optional

LOG_PATH = "/Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis V3/.cursor/debug.log"
SESSION_ID = "debug-session"
RUN_ID = "run1"


def _agent_log(
    location: str,
    message: str,
    data: Optional[dict] = None,
    hypothesis_id: Optional[str] = None,
    run_id: Optional[str] = None,
) -> None:
    try:
        entry = {
            "timestamp": int(time.time() * 1000),
            "location": location,
            "message": message,
            "sessionId": SESSION_ID,
            "runId": run_id or RUN_ID,
        }
        if data is not None:
            entry["data"] = data
        if hypothesis_id is not None:
            entry["hypothesisId"] = hypothesis_id
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
