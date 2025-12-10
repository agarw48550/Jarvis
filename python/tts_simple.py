#!/usr/bin/env python3
"""
TTS with usage tracking to avoid rate limits
"""

import os
import subprocess
import tempfile
import platform
from dotenv import load_dotenv

load_dotenv()

IS_MACOS = platform.system() == "Darwin"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# Track daily usage (reset each session for simplicity)
groq_chars_used = 0
GROQ_DAILY_LIMIT = 3000  # Leave buffer before 3600 limit

VOICES = {
    "calum": "Calum-PlayAI",
    "cillian": "Cillian-PlayAI",
    "atlas": "Atlas-PlayAI",
    "fritz": "Fritz-PlayAI",
    "arista": "Arista-PlayAI",
    "celeste": "Celeste-PlayAI",
}

current_voice = "calum"
speech_enabled = True


def speak_groq(text: str) -> bool:
    global groq_chars_used
    
    if not GROQ_KEY:
        return False
    
    # Check if we're near the limit
    if groq_chars_used + len(text) > GROQ_DAILY_LIMIT:
        print("(Groq TTS limit reached, using local)")
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        
        response = client.audio.speech.create(
            model="playai-tts",
            voice=VOICES.get(current_voice, "Calum-PlayAI"),
            input=text,
            response_format="wav"
        )
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response.write_to_file(f.name)
            audio_path = f.name
        
        subprocess.run(["afplay", audio_path], check=True, timeout=60)
        os.unlink(audio_path)
        
        groq_chars_used += len(text)
        return True
        
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            groq_chars_used = GROQ_DAILY_LIMIT  # Mark as exhausted
        return False


def speak_macos(text: str) -> bool:
    if not IS_MACOS:
        return False
    try:
        subprocess.run(["say", "-v", "Daniel", text], check=True, timeout=60)
        return True
    except:
        return False


def speak(text: str):
    if not speech_enabled or not text:
        return
    
    print("🔊 Speaking...", end=" ", flush=True)
    
    if speak_groq(text):
        print("✓")
    elif speak_macos(text):
        print("✓ (local)")
    else:
        print("✗")


def set_voice(voice: str) -> str:
    global current_voice
    if voice.lower() in VOICES:
        current_voice = voice.lower()
        return f"Voice set to {voice}."
    return f"Unknown voice. Available: {', '.join(VOICES.keys())}"


def list_voices() -> str:
    return f"Available voices: {', '.join(VOICES.keys())}"


def toggle_speech() -> bool:
    global speech_enabled
    speech_enabled = not speech_enabled
    return speech_enabled


def is_speech_enabled() -> bool:
    return speech_enabled
