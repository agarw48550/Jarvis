#!/usr/bin/env python3
"""
Simple Text-to-Speech using pyttsx3 (works offline, cross-platform)
"""

import pyttsx3

# Initialize TTS engine (lazy load)
_engine = None

def get_engine():
    """Get or create TTS engine"""
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        # Set properties
        _engine.setProperty('rate', 175)  # Speed (words per minute)
        _engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
        
        # Try to set a good voice
        voices = _engine.getProperty('voices')
        # Prefer a male voice if available
        for voice in voices:
            if 'male' in voice.name.lower() or 'daniel' in voice.name.lower():
                _engine.setProperty('voice', voice.id)
                break
    
    return _engine

def speak(text: str):
    """Speak the given text"""
    try:
        engine = get_engine()
        print(f"🔊 Speaking...")
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"⚠️ TTS error: {e}")
        print(f"   (Text was: {text})")

def list_voices():
    """List available voices"""
    engine = get_engine()
    voices = engine.getProperty('voices')
    print("\n🎤 Available voices:")
    for i, voice in enumerate(voices):
        print(f"   {i}: {voice.name} ({voice.id})")

def set_voice(voice_index: int):
    """Set voice by index"""
    engine = get_engine()
    voices = engine.getProperty('voices')
    if 0 <= voice_index < len(voices):
        engine.setProperty('voice', voices[voice_index].id)
        print(f"✅ Voice set to: {voices[voice_index].name}")
    else:
        print(f"⚠️ Invalid voice index. Use 0-{len(voices)-1}")

def set_rate(rate: int):
    """Set speech rate (words per minute)"""
    engine = get_engine()
    engine.setProperty('rate', rate)
    print(f"✅ Speech rate set to: {rate} wpm")
