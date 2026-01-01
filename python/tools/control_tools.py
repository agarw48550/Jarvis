#!/usr/bin/env python3
"""Control tools - Music, pause, exit"""

import subprocess


def control_music(action: str) -> str:
    """Control Apple Music"""
    try:
        scripts = {
            "play": 'tell application "Music" to play',
            "pause": 'tell application "Music" to pause',
            "stop": 'tell application "Music" to stop',
            "next": 'tell application "Music" to next track',
            "previous": 'tell application "Music" to previous track',
        }
        
        if action.lower() in scripts:
            subprocess.run(["osascript", "-e", scripts[action.lower()]], timeout=5)
            return f"Music: {action}."
        
        return f"Unknown action. Try: play, pause, next, previous."
    except:
        return "Couldn't control music. Is Music app installed?"


def pause_listening() -> str:
    return "__PAUSE__"


def exit_jarvis() -> str:
    return "__EXIT__"


def stop_speaking() -> str:
    """Interrupt current speech"""
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from interfaces.voice.tts_handler import interrupt_speech
        interrupt_speech()
        return "Speech stopped."
    except:
        return "__STOP_SPEECH__"
