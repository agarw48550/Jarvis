#!/usr/bin/env python3
"""
Backwards compatibility wrapper for tts_simple
Redirects to new modular TTS handler
"""

from interfaces.voice.tts_handler import (
    speak, toggle_speech, is_speech_enabled, 
    set_voice, list_voices, interrupt_speech,
    VOICES, GROQ_VOICES, current_voice, speech_enabled
)

# Backwards compatibility
__all__ = [
    'speak', 'toggle_speech', 'is_speech_enabled',
    'set_voice', 'list_voices', 'interrupt_speech',
    'VOICES', 'GROQ_VOICES', 'current_voice', 'speech_enabled'
]
