import asyncio
import sys
import os
import base64
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_live import GeminiLiveSession

import math

async def verify_pipeline():
    print("🔍 VERIFICATION START: Testing Gemini 2.5 Native Audio Dialog...")
    
    session = GeminiLiveSession()
    
    # Generate 1 second of 440Hz Sine Wave (PCM 16bit 16kHz)
    sample_rate = 16000
    duration = 1.0
    freq = 440.0
    audio_data = bytearray()
    for i in range(int(sample_rate * duration)):
        value = int(32767 * math.sin(2 * math.pi * freq * i / sample_rate))
        audio_data.extend(value.to_bytes(2, byteorder='little', signed=True))
    
    # Chunk it
    chunk_size = 2048
    chunks = [audio_data[i:i + chunk_size] for i in range(0, len(audio_data), chunk_size)]
    
    audio_received = False
    text_received = False
    
    def on_audio(data):
        nonlocal audio_received
        if len(data) > 0:
            if not audio_received:
                print("✅ [Gemini Audio]: Receiving chunks...")
            audio_received = True

    def on_text(text):
        nonlocal text_received
        if text.strip():
            text_received = True
            print(f"✅ [Gemini Text]: {text}")

    try:
        print("🔗 Connecting to Gemini...")
        await session.connect(system_instruction="You are a test agent. Respond with 'Verification successful' and play a short sound or describe your voice.")
        
        # Start receive loop in background
        receive_task = asyncio.create_task(session.receive_loop(on_audio, on_text))
        
        print(f"🎙️ Sending 1s Sine Wave ({len(chunks)} chunks)...")
        for chunk in chunks:
            await session.send_audio_chunk(chunk)
            await asyncio.sleep(0.01) # Stream speed
            
        print("⏳ Waiting for response (timeout 15s)...")
        # Wait for any response
        for _ in range(30):
            if audio_received or text_received:
                break
            await asyncio.sleep(0.5)
            
        if audio_received:
            print("🌟 Pipeline Verified: Native Audio Received!")
        else:
            print("❌ FAILURE: No audio response from Gemini.")
            
        if text_received:
            print("✅ SUCCESS: Received text transcript from Gemini!")
            
    except Exception as e:
        print(f"❌ ERROR encountered during verification: {e}")
    finally:
        await session.close()
        print("🔌 Connection closed.")

if __name__ == "__main__":
    asyncio.run(verify_pipeline())
