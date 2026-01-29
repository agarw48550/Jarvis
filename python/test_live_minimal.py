#!/usr/bin/env python3
"""Minimal Gemini Live connect test: no tools, short system instruction."""
import asyncio
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

async def main():
    key = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
    if not key:
        print("No GEMINI_API_KEY")
        return
    client = genai.Client(api_key=key, http_options={"api_version": "v1beta"})
    model = "models/gemini-2.5-flash-native-audio-preview-12-2025"
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Puck")
            )
        ),
        system_instruction="You are a helpful assistant. Say hello briefly.",
        context_window_compression=types.ContextWindowCompressionConfig(
            trigger_tokens=25600,
            sliding_window=types.SlidingWindow(target_tokens=12800),
        ),
        # NO tools
    )
    print("Connecting (no tools)...")
    start = time.time()
    async with client.aio.live.connect(model=model, config=config) as session:
        print("Connected. Receiving for 20s...")
        n = 0
        async for msg in session.receive():
            n += 1
            if n <= 3 or n % 50 == 0:
                print(f"  msg #{n}")
            if time.time() - start > 20:
                break
    print(f"Done. Received {n} messages in {time.time()-start:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
