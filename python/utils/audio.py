#!/usr/bin/env python3
"""Audio capture and processing utilities"""

import os
import wave
import tempfile
import numpy as np
import pyaudio
from pathlib import Path

TEMP_DIR = Path(tempfile.gettempdir()) / 'jarvis'
TEMP_DIR.mkdir(exist_ok=True)

def record_until_silence(
    max_duration: float = 10.0,
    silence_threshold: int = 500,
    silence_duration:  float = 1.5,
    sample_rate: int = 16000
) -> str:
    """
    Record audio until silence is detected or max duration reached.
    
    Args:
        max_duration: Maximum recording time in seconds
        silence_threshold: RMS threshold for silence detection
        silence_duration: How long silence must last to stop (seconds)
        sample_rate: Audio sample rate
        
    Returns:
        Path to recorded WAV file
    """
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    
    p = pyaudio.PyAudio()
    try:
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=sample_rate,
            input=True,
            frames_per_buffer=CHUNK
        )
        
        print("🎤 Recording...")
        
        frames = []
        silent_chunks = 0
        chunks_for_silence = int(silence_duration * sample_rate / CHUNK)
        max_chunks = int(max_duration * sample_rate / CHUNK)
        
        for _ in range(max_chunks):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
            except Exception as e:
                print(f"Error reading audio: {e}")
                break
            frames.append(data)
            
            # Calculate RMS for silence detection
            audio_array = np.frombuffer(data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_array.astype(np.float32) ** 2))
            
            if rms < silence_threshold:
                silent_chunks += 1
            else:
                silent_chunks = 0
            
            # Stop if silence detected for long enough
            if silent_chunks >= chunks_for_silence and len(frames) > chunks_for_silence: 
                print("🔇 Silence detected, stopping recording")
                break
    finally:
        if 'stream' in locals() and stream.is_active():
            stream.stop_stream()
            stream.close()
        p.terminate()
    
    # Save to WAV file
    output_path = str(TEMP_DIR / 'recorded_audio.wav')
    
    with wave.open(output_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(sample_rate)
        wf.writeframes(b''.join(frames))
    
    print(f"✅ Recorded {len(frames) * CHUNK / sample_rate:.1f} seconds")
    
    return output_path


class AudioCapture:
    """Continuous audio capture for real-time processing"""
    
    def __init__(self, sample_rate=16000, chunk_size=1024):
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.is_recording = False
        self._audio = None
        self._stream = None
    
    def start(self):
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        self.is_recording = True
    
    def read_chunk(self) -> bytes:
        if self._stream and self.is_recording:
            return self._stream.read(self.chunk_size, exception_on_overflow=False)
        return b''
    
    def stop(self):
        self.is_recording = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._audio:
            self._audio.terminate()


class AudioPlayer:
    """Real-time audio player for PCM streaming"""
    
    def __init__(self, sample_rate=24000):
        self.sample_rate = sample_rate
        self._audio = None
        self._stream = None
        self.is_playing = False
        
    def start(self):
        self._audio = pyaudio.PyAudio()
        self._stream = self._audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            output=True
        )
        self.is_playing = True
        
    def play_chunk(self, data: bytes):
        if self._stream and self.is_playing:
            self._stream.write(data)
            
    def stop(self):
        self.is_playing = False
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
        if self._audio:
            self._audio.terminate()
