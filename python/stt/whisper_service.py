#!/usr/bin/env python3
"""Speech-to-Text using Faster Whisper"""

import os
from pathlib import Path

# Global model instance (lazy loaded)
_model = None

def get_model():
    global _model
    if _model is None: 
        print("Loading Whisper model (tiny)...")
        try:
            from faster_whisper import WhisperModel
            _model = WhisperModel(
                "tiny",
                device="cpu",
                compute_type="int8"
            )
            print("✅ Whisper model loaded!")
        except Exception as e:
            print(f"❌ Failed to load Whisper:  {e}")
            raise
    return _model

def transcribe_audio(audio_path:  str) -> str:
    """
    Transcribe audio file to text. 
    
    Args:
        audio_path: Path to audio file (WAV, MP3, etc.)
        
    Returns:
        Transcribed text string
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    
    model = get_model()
    
    # Transcribe with beam search
    segments, info = model.transcribe(
        audio_path,
        beam_size=5,
        language="en",
        vad_filter=True,  # Voice activity detection
        vad_parameters=dict(
            min_silence_duration_ms=500,
            speech_pad_ms=200
        )
    )
    
    # Combine all segments
    text = " ".join([segment.text.strip() for segment in segments])
    
    return text.strip()
