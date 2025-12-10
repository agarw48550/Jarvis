#!/usr/bin/env python3
"""
Text-to-Speech: Groq TTS (cloud) → macOS say (fallback)
"""

import os
import subprocess
import tempfile
import platform
from dotenv import load_dotenv

load_dotenv()

IS_MACOS = platform.system() == "Darwin"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# Voice settings
current_voice = "male"
speech_enabled = True

# Groq voice mapping
GROQ_VOICES = {
    "male": "Fritz-PlayAI",
    "female": "Arista-PlayAI",
    "british": "Basil-PlayAI",
    "casual": "Cillian-PlayAI",
}

# macOS voice mapping
MACOS_VOICES = {
    "male": "Daniel",
    "female": "Samantha",
    "british": "Daniel",
    "casual": "Alex",
}


def speak_groq(text: str) -> bool:
    """Speak using Groq TTS API with SDK"""
    if not GROQ_KEY:
        return False
    
    try:
        from groq import Groq
        
        client = Groq(api_key=GROQ_KEY)
        voice = GROQ_VOICES.get(current_voice, "Fritz-PlayAI")
        
        # Create speech
        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice,
            input=text,
            response_format="wav"
        )
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response.write_to_file(f.name)
            audio_path = f.name
        
        # Play audio
        if IS_MACOS:
            subprocess.run(["afplay", audio_path], check=True, timeout=60)
        else:
            subprocess.run(["aplay", "-q", audio_path], check=True, timeout=60)
        
        os.unlink(audio_path)
        return True
        
    except ImportError:
        print("(install groq: pip install groq)")
        return False
    except Exception as e:
        print(f"(Groq TTS error: {e})")
        return False


def speak_macos(text: str) -> bool:
    """Speak using macOS say command"""
    if not IS_MACOS:
        return False
    
    voice = MACOS_VOICES.get(current_voice, "Samantha")
    clean_text = text.replace('"', "'")
    
    try:
        subprocess.run(
            ["say", "-v", voice, clean_text],
            check=True,
            timeout=60
        )
        return True
    except Exception as e:
        print(f"(say error: {e})")
        return False


# Cloud TTS usage flag
use_cloud_tts = True  # default to using Groq cloud TTS

def speak(text: str):
    """Speak text - tries Groq first (if enabled), then macOS"""
    if not speech_enabled or not text:
        return
    
    print("🔊 Speaking...", end=" ", flush=True)
    
    # Try Groq TTS first if enabled
    if use_cloud_tts and speak_groq(text):
        print("✓")
        return
    
    # Fallback to macOS
    if speak_macos(text):
        print("✓ (local)")
        return
    
    print("✗ (no TTS)")


def set_voice(voice: str):
    global current_voice
    if voice in GROQ_VOICES:
        current_voice = voice
        print(f"✅ Voice: {voice}")



def toggle_speech() -> bool:
    """Toggle speech on/off"""
    global speech_enabled
    speech_enabled = not speech_enabled
    return speech_enabled


def toggle_cloud_tts() -> bool:
    """Toggle between using Groq cloud TTS and local macOS TTS."""
    global use_cloud_tts
    use_cloud_tts = not use_cloud_tts
    print(f"🔀 Cloud TTS {'ON' if use_cloud_tts else 'OFF'}")
    return use_cloud_tts


def is_speech_enabled() -> bool:
    return speech_enabled
