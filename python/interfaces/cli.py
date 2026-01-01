#!/usr/bin/env python3
"""
🤖 JARVIS CLI - Exclusive Gemini 2.5 Native Audio Dialog Model
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Path setup
sys.path.insert(0, str(Path(__file__).parent.parent))
load_dotenv(Path(__file__).parent.parent / ".env")

from core.gemini_live import GeminiLiveSession, MODEL_ID
from core.memory import init_database, get_all_facts, get_facts_for_prompt, get_preferences_for_prompt, get_relevant_context, get_preferences
from core.language_detector import get_language_name
from utils.audio import AudioCapture, AudioPlayer
from tools.tool_registry import TOOLS

# ============== Constants ==============
SYSTEM_PROMPT_TEMPLATE = """You are Jarvis, an intelligent, helpful, and proactive AI assistant.
Your voice is Charon, a deep and professional tone.

## CORE RULES
1. ALWAYS respond in audio natively.
2. Keep responses CONCISE (max 25 words).
3. Be proactive and helpful.

## MEMORY & PREFERENCES
{preferences}
{user_facts}

## AVAILABLE TOOLS
{tools_description}
"""

def build_tools_description() -> str:
    lines = []
    for name, info in TOOLS.items():
        params = ", ".join(f"{k}: {v}" for k, v in info["parameters"].items()) or "none"
        lines.append(f"- {name}: {info['description']}")
    return "\n".join(lines)

def build_system_prompt() -> str:
    # Simplified context-less prompt for initial start
    return SYSTEM_PROMPT_TEMPLATE.format(
        preferences=get_preferences_for_prompt(),
        user_facts=get_facts_for_prompt(),
        tools_description=build_tools_description()
    )

def print_header():
    print("\n" + "=" * 60)
    print("🤖 JARVIS - Native Audio Dialog Mode")
    print("=" * 60)
    print(f"Model: {MODEL_ID}")
    print("Direct WebSocket pipeline connected.")
    print("Commands: Speak naturally. Ctrl+C to exit.")
    print("=" * 60 + "\n")

async def run_live_session():
    print("🔴 Initializing Native Audio Stream...")
    
    session = GeminiLiveSession(voice_name="Charon")
    player = AudioPlayer(sample_rate=24000)
    recorder = AudioCapture(sample_rate=16000, chunk_size=1024)
    
    stop_event = asyncio.Event()
    try:
        # Start Hardware
        player.start()
        recorder.start()
        
        # Connect to Gemini
        await session.connect(system_instruction=build_system_prompt())
        
        loop = asyncio.get_running_loop()

        audio_queue = asyncio.Queue()

        def on_audio(pcm_data):
            audio_queue.put_nowait(pcm_data)

        def on_text(text):
            print(text, end="", flush=True)

        async def play_audio_queue():
            try:
                while not stop_event.is_set():
                    pcm_data = await audio_queue.get()
                    await loop.run_in_executor(None, player.play_chunk, pcm_data)
                    audio_queue.task_done()
            except Exception as e:
                print(f"\nPlayback Error: {e}")

        async def send_mic_input():
            print("🚀 Jarvis is Online. Speak now!")
            try:
                while not stop_event.is_set():
                    chunk = await loop.run_in_executor(None, recorder.read_chunk)
                    if chunk:
                        await session.send_audio_chunk(chunk)
            except Exception as e:
                print(f"\nMic Error: {e}")

        receive_task = asyncio.create_task(session.receive_loop(on_audio, on_text))
        send_task = asyncio.create_task(send_mic_input())
        play_task = asyncio.create_task(play_audio_queue())
        
        # Wait for either to finish (e.g. error) or stay running
        await asyncio.gather(receive_task, send_task, play_task)

    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\n❌ Pipeline Error: {e}")
    finally:
        print("\n🔌 Disconnecting...")
        stop_event.set()
        recorder.stop()
        player.stop()
        await session.close()

def main():
    try:
        init_database()
    except: pass
    
    print_header()
    
    try:
        asyncio.run(run_live_session())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()
