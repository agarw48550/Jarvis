import subprocess


def _osascript(lines: list[str]) -> tuple[bool, str]:
    script = "\n".join(lines)
    try:
        out = subprocess.check_output(["osascript", "-e", script], text=True, stderr=subprocess.STDOUT)
        return True, (out or "").strip()
    except subprocess.CalledProcessError as e:
        return False, (e.output or str(e))
    except FileNotFoundError:
        return False, "osascript not found (macOS only)."


def open_app(app_name: str) -> str:
    name = (app_name or "").strip()
    if not name:
        return "Missing app name."
    try:
        subprocess.check_call(["open", "-a", name])
        return f"Opening {name}."
    except subprocess.CalledProcessError as e:
        return f"Couldn't open {name}: {e}"
    except FileNotFoundError:
        return "'open' command not found."


def quit_app(app_name: str) -> str:
    name = (app_name or "").strip()
    if not name:
        return "Missing app name."
    ok, out = _osascript([f'tell application "{name}" to quit'])
    return "OK" if ok else out


def close_window() -> str:
    ok, out = _osascript(['tell application "System Events" to keystroke "w" using {command down}'])
    return "Closed window." if ok else out


def fullscreen_toggle() -> str:
    ok, out = _osascript(['tell application "System Events" to keystroke "f" using {control down, command down}'])
    return "Toggled fullscreen." if ok else out


def get_volume() -> int:
    ok, out = _osascript(['output volume of (get volume settings)'])
    if ok:
        try:
            return int(out.strip())
        except Exception:
            return -1
    return -1


def set_volume(percent: int) -> str:
    try:
        v = int(percent)
    except Exception:
        return "Volume must be an integer 0-100."
    v = max(0, min(100, v))
    ok, out = _osascript([f'set volume output volume {v}'])
    return f"Volume {v}%." if ok else out


def mute() -> str:
    ok, out = _osascript(['set volume with output muted'])
    return "Muted." if ok else out


def unmute() -> str:
    ok, out = _osascript(['set volume without output muted'])
    return "Unmuted." if ok else out


def volume_up(step: int = 10) -> str:
    cur = get_volume()
    if cur < 0:
        return "Couldn't read current volume."
    return set_volume(cur + step)


def volume_down(step: int = 10) -> str:
    cur = get_volume()
    if cur < 0:
        return "Couldn't read current volume."
    return set_volume(cur - step)
