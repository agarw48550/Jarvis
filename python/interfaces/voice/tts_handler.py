#!/usr/bin/env python3
"""
Text-to-Speech Handler with Groq TTS and macOS fallback
Fixed version with proper error handling and multi-language support
"""

import os
import re
import subprocess
import tempfile
import platform
from dotenv import load_dotenv
from typing import Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.language_detector import detect_language_from_text, get_language_name

load_dotenv()

IS_MACOS = platform.system() == "Darwin"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# Track Groq TTS usage
groq_chars_used = 0
GROQ_LIMIT = 2500  # Conservative daily limit

# Current speech process (for interruption)
current_speech_process = None
speech_interrupted = False
MAX_TTS_CHARLEN = int(os.getenv("MAX_TTS_CHARLEN", "260"))

# Groq voices (PlayAI)
GROQ_VOICES = {
    "calum": "Calum-PlayAI",
    "cillian": "Cillian-PlayAI",
    "atlas": "Atlas-PlayAI",
    "arista": "Arista-PlayAI",
}

# Edge TTS voices (High Quality, Free)
EDGE_VOICES = {
    "aria": "en-US-AriaNeural",
    "guy": "en-US-GuyNeural",
    "jenny": "en-US-JennyNeural",
    "michelle": "en-US-MichelleNeural",
    "roger": "en-US-RogerNeural",
    "brian": "en-GB-BrianNeural",   # British Male
    "sonia": "en-GB-SoniaNeural",   # British Female
    "natasha": "en-AU-NatashaNeural", # Australian Female
    "william": "en-AU-WilliamNeural", # Australian Male
}

# Default voices
current_voice = "calum"      # Default Groq voice
current_edge_voice = "aria"  # Default Edge voice
speech_enabled = True


def check_groq_sdk() -> tuple[bool, Optional[str]]:
    """Check if Groq SDK is available"""
    try:
        import groq
        return True, None
    except ImportError:
        return False, "groq package not installed. Install with: pip install groq"


def interrupt_speech():
    """Stop current speech"""
    global current_speech_process, speech_interrupted
    speech_interrupted = True
    if current_speech_process:
        try:
            current_speech_process.terminate()
            current_speech_process.wait(timeout=1)
            current_speech_process = None
        except Exception:
            try:
                current_speech_process.kill()
            except Exception:
                pass
            current_speech_process = None


def speak_groq(text: str, voice: Optional[str] = None) -> bool:
    """
    Speak using Groq TTS (English only).
    Returns True if successful, False otherwise.
    """
    global groq_chars_used, current_speech_process
    
    # Check SDK availability
    sdk_ok, error = check_groq_sdk()
    if not sdk_ok:
        print("\n⚠️ Groq SDK missing (pip install groq)")
        return False
    
    # Check API key
    if not GROQ_KEY:
        print("\n⚠️ No GROQ_API_KEY for TTS")
        return False
    
    # Check quota
    if groq_chars_used + len(text) > GROQ_LIMIT:
        return False
    
    # Groq TTS only supports English well
    detected_lang = detect_language_from_text(text)
    if detected_lang != "en":
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        
        voice_name = GROQ_VOICES.get(voice or current_voice, "Calum-PlayAI")
        
        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice_name,
            input=text,
            response_format="wav"
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response.write_to_file(f.name)
            audio_path = f.name
        
        # Play on macOS
        if IS_MACOS:
            current_speech_process = subprocess.Popen(
                ["afplay", audio_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            current_speech_process.wait()
            os.unlink(audio_path)
            current_speech_process = None
            groq_chars_used += len(text)
            return True
        else:
            os.unlink(audio_path)
            return False
        
    except ImportError:
        print("\n⚠️ Groq SDK import failed for TTS")
        return False
    except Exception as e:
        error_str = str(e).lower()
        print(f"\n⚠️ Groq TTS error: {str(e)[:120]}")
        if "rate_limit" in error_str or "429" in error_str or "quota" in error_str:
            groq_chars_used = GROQ_LIMIT  # Mark as exhausted
        return False


def speak_macos(text: str, language: Optional[str] = None) -> bool:
    """
    Speak using macOS say command with language-appropriate voice.
    Returns True if successful, False otherwise.
    """
    global current_speech_process
    
    if not IS_MACOS:
        return False
    
    try:
        current_speech_process = subprocess.Popen(
            ["say", text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        current_speech_process.wait()
        current_speech_process = None
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


import asyncio

def speak_edge_tts(text: str, voice: str = "en-US-AriaNeural") -> bool:
    """
    Speak using Microsoft Edge TTS (Free, High Quality).
    """
    global current_speech_process
    
    try:
        import edge_tts
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            audio_path = f.name
            
        async def _gen():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(audio_path)
            
        asyncio.run(_gen())
        
        # Play on macOS
        if IS_MACOS:
            current_speech_process = subprocess.Popen(
                ["afplay", audio_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            current_speech_process.wait()
            os.unlink(audio_path)
            current_speech_process = None
            return True
            
    except Exception as e:
        print(f"\n⚠️ Edge TTS error: {e}")
        if 'audio_path' in locals() and os.path.exists(audio_path):
            os.unlink(audio_path)
        return False
    
    return False


def speak(text: str, language: Optional[str] = None, prefer_groq: bool = True):
    """
    Main TTS function with automatic fallback.
    Priority: Groq (if en) -> Edge TTS (High Quality) -> macOS (Offline)
    """
    global speech_interrupted
    
    if not speech_enabled or not text or not text.strip():
        return
    
    speech_interrupted = False
    prepared_text = _prepare_tts_text(text)
    if not prepared_text:
        return
        
    # 1. Try Groq (English Only, if quota available)
    if prefer_groq and not speech_interrupted:
        if speak_groq(prepared_text):
            return

    # 2. Try Edge TTS (High Quality, Free)
    if not speech_interrupted:
        # Use selected edge voice if available, otherwise map language
        voice_to_use = EDGE_VOICES.get(current_edge_voice, "en-US-AriaNeural")
        
        # Override for specific languages if not English
        if language == "zh": voice_to_use = "zh-CN-XiaoxiaoNeural"
        elif language == "es": voice_to_use = "es-ES-ElviraNeural"
        elif language == "fr": voice_to_use = "fr-FR-DeniseNeural"
        elif language == "de": voice_to_use = "de-DE-KatjaNeural"
        elif language == "ja": voice_to_use = "ja-JP-NanamiNeural"
        
        if speak_edge_tts(prepared_text, voice=voice_to_use):
            return

    # 3. Fallback to macOS (Offline)
    if not speech_interrupted:
        speak_macos(prepared_text, language)


def _prepare_tts_text(text: str) -> str:
    """
    Normalize text for TTS and enforce a maximum length so speech stays short.
    """
    if not text:
        return ""
    
    cleaned = re.sub(r'\s+', ' ', text).strip()
    if not cleaned:
        return ""
    
    if len(cleaned) <= MAX_TTS_CHARLEN:
        return cleaned
    
    # Try to cut at sentence boundary before limit
    truncated = cleaned[:MAX_TTS_CHARLEN]
    last_period = truncated.rfind('. ')
    last_comma = truncated.rfind(', ')
    cut_idx = max(last_period, last_comma)
    if cut_idx > MAX_TTS_CHARLEN * 0.5:
        truncated = truncated[:cut_idx + 1]
    else:
        truncated = truncated.rstrip() + "..."
    
    return truncated


def set_voice(voice: str) -> str:
    """Set Groq or Edge TTS voice preference"""
    global current_voice, current_edge_voice
    
    voice_lower = voice.lower()
    
    # Check Groq voices
    if voice_lower in GROQ_VOICES:
        current_voice = voice_lower
        return f"Groq voice changed to {voice}."
        
    # Check Edge voices
    if voice_lower in EDGE_VOICES:
        current_edge_voice = voice_lower
        return f"Edge TTS voice changed to {voice}."
        
    return f"Voice '{voice}' not found. Available: {', '.join(list(GROQ_VOICES.keys()) + list(EDGE_VOICES.keys()))}"


def list_voices() -> str:
    """List all available voices"""
    groq = ", ".join(GROQ_VOICES.keys())
    edge = ", ".join(EDGE_VOICES.keys())
    return f"Groq (Fast): {groq}\nEdge TTS (High Quality): {edge}"


def toggle_speech() -> bool:
    """Toggle speech on/off"""
    global speech_enabled
    speech_enabled = not speech_enabled
    return speech_enabled


def is_speech_enabled() -> bool:
    """Check if speech is enabled"""
    return speech_enabled


def get_groq_usage() -> dict:
    """Get Groq TTS usage statistics"""
    return {
        "characters_used": groq_chars_used,
        "limit": GROQ_LIMIT,
        "remaining": max(0, GROQ_LIMIT - groq_chars_used),
        "available": groq_chars_used < GROQ_LIMIT
    }


# Backwards compatibility
VOICES = GROQ_VOICES
