#!/usr/bin/env python3
"""
🤖 JARVIS v5 - Full Conversational AI Assistant

Features:
- Always-on voice mode (continuous conversation)
- Groq TTS for natural speech
- Actions: search, open apps, reminders, time, volume
- Persistent memory
"""

import os
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from llm_router import chat, check_api_keys, detect_action
from memory import get_facts_for_prompt, add_fact, get_all_facts, clear_memory
from tts_simple import speak, toggle_speech, is_speech_enabled, set_voice, toggle_cloud_tts
from stt_cloud import listen
from actions import ACTIONS, get_time

# ============== Config ==============
VOICE_MODE = True  # Always listen by default

SYSTEM_PROMPT = """You are Jarvis, a fast and friendly voice assistant.

RULES:
1. Keep responses VERY SHORT (1 sentence preferred, 2 max)
2. Be conversational, natural, friendly
3. When user shares info, output: [REMEMBER: fact]
4. For actions you can't do, be helpful but brief

{user_facts}

You can help with: searching the web, opening apps, setting reminders, checking time, controlling volume.

Example responses:
- "Sure thing!"
- "Got it, opening Safari now."
- "It's 3:45 PM."
- "I'll remember that!"
"""


def build_prompt() -> str:
    return SYSTEM_PROMPT.format(user_facts=get_facts_for_prompt())


def extract_memories(response: str) -> str:
    pattern = r'\[REMEMBER:\s*([^\]]+)\]'
    for fact in re.findall(pattern, response):
        add_fact(fact.strip())
    return re.sub(pattern, '', response).strip()


def print_header():
    print("\n" + "=" * 50)
    print("🤖 JARVIS v5 - Voice Assistant")
    print("=" * 50)
    print("Voice mode ON - Just speak! Or type if you prefer.")
    print("Commands: 'type' | 'memory' | 'mute' | 'quit'")
    print("=" * 50 + "\n")


def get_input() -> str:
    """Get input via voice or keyboard"""
    global VOICE_MODE
    
    if VOICE_MODE:
        text = listen()
        if text:
            print(f"👤 You: {text}")
            return text
        else:
            # No speech detected, wait for another attempt
            return None
    else:
        return input("👤 You: ").strip()


def main():
    global VOICE_MODE
    
    print_header()
    check_api_keys()
    
    messages = []
    
    # Personalized greeting
    facts = get_all_facts()
    name = None
    for f in facts:
        fact_text = f.get("fact", "").lower()
        if "name is" in fact_text:
            name = fact_text.split("name is")[-1].strip().split()[0].title()
            break
    
    greeting = f"Hey {name}! What can I do for you?" if name else "Hey! I'm Jarvis. What's your name?"
    print(f"🤖 {greeting}")
    speak(greeting)
    
    while True:
        try:
            print()  # Spacing
            user_input = get_input()
            
            if not user_input:
                continue
            
            lower_input = user_input.lower().strip()
            
            # === Commands ===
            if lower_input == 'quit' or lower_input in ['goodbye', 'bye', 'exit']:
                bye = "See you later!"
                print(f"\n🤖 {bye}")
                speak(bye)
                break
            
            if lower_input == 'type':
                VOICE_MODE = False
                print("⌨️ Switched to typing mode. Say 'voice' to switch back.")
                continue
            
            if lower_input == 'voice':
                VOICE_MODE = True
                print("🎤 Switched to voice mode.")
                continue
            
            if lower_input == 'memory':
                facts = get_all_facts()
                if facts:
                    print("\n📚 I remember:")
                    for f in facts:
                        print(f"   • {f['fact']}")
                else:
                    print("\n📚 No memories yet.")
                continue
            
            if lower_input == 'mute':
                enabled = toggle_speech()
                print(f"🔊 Speech {'ON' if enabled else 'OFF'}")
                continue
            
            if lower_input == 'clear memory':
                clear_memory()
                messages = []
                print("🗑️ Memory cleared.")
                continue
            
            # === Check for direct actions ===
            action_name, params = detect_action(user_input)
            
            if action_name and action_name in ACTIONS:
                action_fn = ACTIONS[action_name]
                try:
                    if params:
                        result = action_fn(**params)
                    else:
                        result = action_fn()
                    print(f"\n🤖 {result}")
                    speak(result)
                    continue
                except Exception as e:
                    print(f"⚠️ Action failed: {e}")
            
            # === Chat with LLM ===
            messages.append({"role": "user", "content": user_input})
            if len(messages) > 10:
                messages = messages[-10:]
            
            response = chat(messages, build_prompt())
            clean_response = extract_memories(response)
            
            messages.append({"role": "assistant", "content": clean_response})
            
            print(f"\n🤖 {clean_response}")
            speak(clean_response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
