#!/usr/bin/env python3
"""
Backwards compatibility wrapper for stt_cloud
Redirects to new modular STT handler
"""

from interfaces.voice.stt_handler import listen, transcribe_groq, check_dependencies

# Backwards compatibility
__all__ = ['listen', 'transcribe_groq', 'check_dependencies']
