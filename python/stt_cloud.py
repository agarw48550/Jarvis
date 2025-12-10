#!/usr/bin/env python3
"""
Cloud Speech-to-Text with Voice Activity Detection
Records until silence is detected, then transcribes via Groq Whisper
"""

import os
import subprocess
import tempfile
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY", "")


def record_until_silence(max_duration: int = 15, silence_duration: float = 1.5) -> str:
    """
    Record audio until silence is detected.
    Uses sox's silence detection feature.
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_path = temp_file.name
    temp_file.close()
    
    print("🎤 Listening...", end=" ", flush=True)
    
    try:
        # Record with silence detection
        # silence 1 = detect silence at start (skip initial silence)
        # silence 2 = stop after silence_duration of silence
        subprocess.run([
            "rec", "-q", audio_path,
            "rate", "16k",
            "channels", "1",
            "silence", "1", "0.1", "1%",  # Skip initial silence
            "1", str(silence_duration), "1%",  # Stop after silence
            "trim", "0", str(max_duration)  # Max duration cap
        ], timeout=max_duration + 5, check=True)
        
        # Check if file has content
        file_size = os.path.getsize(audio_path)
        if file_size < 1000:  # Too small, probably just noise
            print("(no speech detected)")
            os.unlink(audio_path)
            return None
            
        print("✓")
        return audio_path
        
    except subprocess.TimeoutExpired:
        print("(timeout)")
        if os.path.exists(audio_path):
            return audio_path
        return None
    except FileNotFoundError:
        print("\n⚠️ 'sox' not installed. Run: brew install sox")
        return None
    except Exception as e:
        print(f"\n⚠️ Recording error: {e}")
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        return None


def transcribe_groq(audio_path: str) -> str:
    """Transcribe audio using Groq Whisper API"""
    if not GROQ_KEY:
        raise Exception("No Groq API key")
    
    print("📝 Processing...", end=" ", flush=True)
    
    with open(audio_path, "rb") as f:
        response = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            files={"file": f},
            data={"model": "whisper-large-v3-turbo", "response_format": "text"},
            timeout=30
        )
    
    if response.status_code == 200:
        text = response.text.strip()
        if text and text != ".":
            print(f"✓")
            return text
        print("(empty)")
        return None
    
    print(f"✗")
    raise Exception(f"STT error: {response.status_code}")


def listen() -> str:
    """Record and transcribe. Returns text or None."""
    audio_path = record_until_silence()
    
    if not audio_path:
        return None
    
    try:
        text = transcribe_groq(audio_path)
        os.unlink(audio_path)
        return text
    except Exception as e:
        print(f"⚠️ {e}")
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        return None
