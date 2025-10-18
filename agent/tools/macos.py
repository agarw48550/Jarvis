import subprocess
import threading
import time
import re
from datetime import timedelta


def _run_osascript(script: str) -> str:
    try:
        out = subprocess.check_output(["osascript", "-e", script], text=True)
        return (out or "").strip()
    except subprocess.CalledProcessError as e:
        return f"AppleScript error: {e.output.strip() if e.output else e}"
    except FileNotFoundError:
        return "osascript not found (macOS only)."


def music(action: str) -> str:
    action = (action or "").lower().strip()
    mapping = {
        "play": 'tell application "Music" to play',
        "pause": 'tell application "Music" to pause',
        "toggle": 'tell application "Music" to playpause',
        "next": 'tell application "Music" to next track',
        "previous": 'tell application "Music" to previous track',
    }
    script = mapping.get(action)
    if not script:
        return "Unsupported music action. Use play, pause, toggle, next, previous."
    res = _run_osascript(script)
    return "OK" if not res.lower().startswith("applescript error") else res


def battery_status() -> str:
    try:
        out = subprocess.check_output(["pmset", "-g", "batt"], text=True)
    except FileNotFoundError:
        return "pmset not found (macOS only)."
    except subprocess.CalledProcessError as e:
        return f"Battery query error: {e.output.strip() if e.output else e}"
    # Parse percentage and state/time
    perc = None
    m = re.search(r"(\d+)%", out)
    if m:
        perc = int(m.group(1))
    # State may include: discharging; charging; charged; AC attached
    state = ""
    if "discharging" in out:
        state = "discharging"
    elif "charging" in out:
        state = "charging"
    elif "charged" in out:
        state = "charged"
    elif "AC attached" in out or "AC Power" in out:
        state = "AC power"
    rem = None
    m2 = re.search(r"(\d+:\d+) remaining", out)
    if m2:
        rem = m2.group(1)
    if perc is None:
        return out.strip()
    parts = [f"Battery {perc}%"]
    if state:
        parts.append(f"({state}")
        if rem and state == "discharging":
            parts[-1] += f", {rem} remaining)"
        else:
            parts[-1] += ")"
    return " ".join(parts)


# Simple in-process timer & stopwatch
_timers_lock = threading.Lock()
_timers: dict[int, float] = {}
_timer_id_seq = 0
_timer_worker_started = False


def _timer_worker():
    global _timers
    while True:
        time.sleep(0.2)
        now = time.time()
        expired = []
        with _timers_lock:
            for tid, end_at in list(_timers.items()):
                if now >= end_at:
                    expired.append(tid)
            for tid in expired:
                _timers.pop(tid, None)
        if expired:
            # Non-blocking macOS sound + optional TTS via 'say'
            try:
                subprocess.Popen(["afplay", "/System/Library/Sounds/Glass.aiff"])  # fire-and-forget
            except Exception:
                pass
            try:
                subprocess.Popen(["say", "Timer done"])  # audible notification
            except Exception:
                pass


def start_timer(seconds: int) -> str:
    global _timer_id_seq, _timer_worker_started
    if seconds <= 0:
        return "Timer duration must be positive."
    with _timers_lock:
        _timer_id_seq += 1
        tid = _timer_id_seq
        _timers[tid] = time.time() + seconds
        if not _timer_worker_started:
            t = threading.Thread(target=_timer_worker, daemon=True)
            t.start()
            _timer_worker_started = True
    td = timedelta(seconds=seconds)
    return f"Timer set for {td}. (id={tid})"


def cancel_timers() -> str:
    with _timers_lock:
        n = len(_timers)
        _timers.clear()
    return f"Cancelled {n} timer(s)."


def timers_status() -> str:
    with _timers_lock:
        if not _timers:
            return "No active timers."
        now = time.time()
        remaining = [max(0, int(end - now)) for end in _timers.values()]
    return "Active timers: " + ", ".join(f"{r}s" for r in remaining)


# Stopwatch
_stopwatch_lock = threading.Lock()
_stopwatch_start: float | None = None
_stopwatch_running = False


def stopwatch_start() -> str:
    global _stopwatch_start, _stopwatch_running
    with _stopwatch_lock:
        if _stopwatch_running:
            return "Stopwatch already running."
        _stopwatch_start = time.time()
        _stopwatch_running = True
        return "Stopwatch started."


def stopwatch_stop() -> str:
    global _stopwatch_start, _stopwatch_running
    with _stopwatch_lock:
        if not _stopwatch_running:
            return "Stopwatch is not running."
        elapsed = time.time() - (_stopwatch_start or time.time())
        _stopwatch_running = False
        _stopwatch_start = None
        return f"Stopwatch stopped at {timedelta(seconds=int(elapsed))}."


def stopwatch_reset() -> str:
    global _stopwatch_start, _stopwatch_running
    with _stopwatch_lock:
        _stopwatch_start = None
        _stopwatch_running = False
    return "Stopwatch reset."


def stopwatch_status() -> str:
    with _stopwatch_lock:
        if not _stopwatch_running or _stopwatch_start is None:
            return "Stopwatch is not running."
        elapsed = time.time() - _stopwatch_start
        return f"Stopwatch: {timedelta(seconds=int(elapsed))}."


def run_shortcut(name: str, input_text: str | None = None) -> str:
    name = (name or "").strip()
    if not name:
        return "Missing shortcut name."
    cmd = ["shortcuts", "run", name]
    if input_text:
        cmd += ["--input", input_text]
    try:
        out = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)
        return (out or "OK").strip()
    except FileNotFoundError:
        return "Shortcuts CLI not found. Ensure you're on macOS Monterey+ and 'shortcuts' is available."
    except subprocess.CalledProcessError as e:
        txt = e.output.strip() if e.output else str(e)
        return f"Shortcut error: {txt}"
