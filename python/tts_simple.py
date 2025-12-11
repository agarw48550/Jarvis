#!/usr/bin/env python3
"""
Multilingual TTS with interrupt support
"""

import os
import subprocess
import tempfile
import platform
from dotenv import load_dotenv

load_dotenv()

IS_MACOS = platform.system() == "Darwin"
GROQ_KEY = os.getenv("GROQ_API_KEY", "")

# Track usage
groq_chars_used = 0
GROQ_LIMIT = 2500  # Conservative limit

# Current speech process (for interruption)
current_speech_process = None
speech_interrupted = False

# Groq voices
GROQ_VOICES = {
    "calum": "Calum-PlayAI",
    "cillian": "Cillian-PlayAI",
    "atlas": "Atlas-PlayAI",
    "arista": "Arista-PlayAI",
}

# macOS voices by language
MACOS_VOICES = {
    "en": "Daniel",
    "zh": "Ting-Ting",      # Mandarin Chinese
    "zh-TW": "Mei-Jia",     # Taiwanese Mandarin
    "ja": "Kyoko",          # Japanese
    "ko": "Yuna",           # Korean
    "es": "Monica",         # Spanish
    "fr": "Thomas",         # French
    "de": "Anna",           # German
    "it": "Alice",          # Italian
    "pt": "Luciana",        # Portuguese
    "ru": "Milena",         # Russian
    "ar": "Maged",          # Arabic
    "hi": "Lekha",          # Hindi
}

current_voice = "calum"
speech_enabled = True


def detect_language(text: str) -> str:
    """Simple language detection based on character ranges"""
    # Chinese
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        return "zh"
    # Japanese (Hiragana/Katakana)
    if any('\u3040' <= char <= '\u30ff' for char in text):
        return "ja"
    # Korean
    if any('\uac00' <= char <= '\ud7af' for char in text):
        return "ko"
    # Arabic
    if any('\u0600' <= char <= '\u06ff' for char in text):
        return "ar"
    # Russian/Cyrillic
    if any('\u0400' <= char <= '\u04ff' for char in text):
        return "ru"
    # Default to English
    return "en"


def interrupt_speech():
    """Stop current speech"""
    global current_speech_process, speech_interrupted
    speech_interrupted = True
    if current_speech_process:
        try:
            current_speech_process.terminate()
            current_speech_process = None
        except:
            pass


def speak_groq(text: str) -> bool:
    """Speak using Groq TTS (English only)"""
    global groq_chars_used, current_speech_process
    
    if not GROQ_KEY or groq_chars_used + len(text) > GROQ_LIMIT:
        return False
    
    # Groq only supports English well
    if detect_language(text) != "en":
        return False
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        
        response = client.audio.speech.create(
            model="playai-tts",
            voice=GROQ_VOICES.get(current_voice, "Calum-PlayAI"),
            input=text,
            response_format="wav"
        )
        
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            response.write_to_file(f.name)
            audio_path = f.name
        
        current_speech_process = subprocess.Popen(["afplay", audio_path])
        current_speech_process.wait()
        os.unlink(audio_path)
        
        groq_chars_used += len(text)
        current_speech_process = None
        return True
        
    except Exception as e:
        if "rate_limit" in str(e).lower() or "429" in str(e):
            groq_chars_used = GROQ_LIMIT
        return False


def speak_macos(text: str) -> bool:
    """Speak using macOS with language-appropriate voice"""
    global current_speech_process
    
    if not IS_MACOS:
        return False
    
    lang = detect_language(text)
    voice = MACOS_VOICES.get(lang, "Daniel")
    
    try:
        current_speech_process = subprocess.Popen(
            ["say", "-v", voice, text],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        current_speech_process.wait()
        current_speech_process = None
        return True
    except:
        return False


def speak(text: str):
    """Speak text with language detection"""
    global speech_interrupted
    
    if not speech_enabled or not text:
        return
    
    speech_interrupted = False
    print("🔊 Speaking...", end=" ", flush=True)
    
    # Try Groq for English
    if detect_language(text) == "en" and speak_groq(text):
        print("✓" if not speech_interrupted else "(interrupted)")
        return
    
    # Use macOS for any language
    if speak_macos(text):
        print("✓" if not speech_interrupted else "(interrupted)")
        return
    
    print("✗")


def set_voice(voice: str) -> str:
    global current_voice
    if voice.lower() in GROQ_VOICES:
        current_voice = voice.lower()
        return f"Voice changed to {voice}."
    return f"Unknown voice. Available: {', '.join(GROQ_VOICES.keys())}"


def list_voices() -> str:
    return f"Voices: {', '.join(GROQ_VOICES.keys())}"


def toggle_speech() -> bool:
    global speech_enabled
    speech_enabled = not speech_enabled
    return speech_enabled


def is_speech_enabled() -> bool:
    return speech_enabled


# For backwards compatibility
VOICES = GROQ_VOICES
