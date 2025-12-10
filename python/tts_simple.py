#!/usr/bin/env python3
"""
Text-to-Speech: Groq TTS (Calum voice) → macOS fallback
"""

import os
import subprocess
import tempfile
import platform
from dotenv import load_dotenv

load_dotenv()

IS_MACOS = platform.system() == "Darwin"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# Available Groq voices
VOICES = {
    "calum": "Calum-PlayAI",      # Natural, friendly male
    "cillian": "Cillian-PlayAI",  # Casual male
    "atlas": "Atlas-PlayAI",      # Professional male
    "fritz": "Fritz-PlayAI",      # Clear male
    "arista": "Arista-PlayAI",    # Female
    "celeste": "Celeste-PlayAI",  # Female
    "quinn": "Quinn-PlayAI",      # Neutral
}

# macOS fallback
MACOS_VOICES = {"male": "Daniel", "female": "Samantha"}

current_voice = "calum"  # Default to Calum
speech_enabled = True


def speak_groq(text: str) -> bool:
    """Speak using Groq TTS"""
    if not GROQ_KEY:
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        
        voice_id = VOICES.get(current_voice, "Calum-PlayAI")
        
        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice_id,
            input=text,
            response_format="wav"
        )
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response.write_to_file(f.name)
            audio_path = f.name
        
        if IS_MACOS:
            subprocess.run(["afplay", audio_path], check=True, timeout=60)
        else:
            subprocess.run(["aplay", "-q", audio_path], check=True, timeout=60)
        
        os.unlink(audio_path)
        return True
        
    except Exception as e:
        print(f"(TTS error: {e})")
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
        return
    
    if speak_macos(text):
        print("✓ (local)")
        return
    
    print("✗")


def set_voice(voice: str):
    global current_voice
    voice = voice.lower()
    if voice in VOICES:
        current_voice = voice
        return f"Voice changed to {voice}."
    return f"Unknown voice. Available: {', '.join(VOICES.keys())}"


def list_voices() -> str:
    return "Available voices: " + ", ".join(VOICES.keys())


def toggle_speech() -> bool:
    global speech_enabled
    speech_enabled = not speech_enabled
    return speech_enabled


def is_speech_enabled() -> bool:
    return speech_enabled
