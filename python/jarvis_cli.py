#!/usr/bin/env python3
"""
🤖 JARVIS v6 - True Agentic AI Assistant

The LLM decides which tools to use and executes them automatically.
"""

import os
import sys
import json
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from llm_router import chat, check_api_keys
from memory import get_facts_for_prompt, add_fact, get_all_facts, clear_memory
from tts_simple import speak, toggle_speech, is_speech_enabled, set_voice, list_voices
from stt_cloud import listen
from actions import TOOLS

# ============== Agentic System Prompt ==============

SYSTEM_PROMPT = """You are Jarvis, an intelligent voice assistant. You can perform actions using tools.

## AVAILABLE TOOLS
{tools_description}

## HOW TO USE TOOLS
When you need to perform an action, output a JSON block:
```tool
{{"tool": "tool_name", "params": {{"param1": "value1"}}}}
```

## RULES
1. ALWAYS use tools when the user asks you to DO something
2. Keep spoken responses SHORT (1-2 sentences)
3. After using a tool, briefly confirm what you did
4. When user shares personal info, output: [REMEMBER: fact]
5. Be natural and conversational

## USER INFO
{user_facts}

## EXAMPLES

User: "What time is it?"
You: ```tool
{{"tool": "get_time", "params": {{}}}}
```

User: "Open Safari"
You: ```tool
{{"tool": "open_app", "params": {{"app_name": "Safari"}}}}
```

User: "Search for pizza near me"
You: ```tool
{{"tool": "search_web", "params": {{"query": "pizza near me"}}}}
```

User: "Set volume to 50%"
You: ```tool
{{"tool": "set_volume", "params": {{"level": 50}}}}
```

User: "Turn up the volume"
You: ```tool
{{"tool": "set_volume", "params": {{"action": "up"}}}}
```

User: "Remind me to call mom"
You: ```tool
{{"tool": "add_reminder", "params": {{"text": "call mom"}}}}
```

User: "What are my reminders?"
You: ```tool
{{"tool": "get_reminders", "params": {{}}}}
```

User: "Stop listening" or "Pause"
You: ```tool
{{"tool": "pause_listening", "params": {{}}}}
```

User: "Change voice to cillian"
You: I'll change the voice for you. [VOICE: cillian]

User: "What voices are available?"
You: Available voices: calum, cillian, atlas, fritz, arista, celeste, quinn."""


def build_tools_description() -> str:
    lines = []
    for name, info in TOOLS.items():
        params = ", ".join(f"{k}: {v}" for k, v in info["parameters"].items()) or "none"
        lines.append(f"- {name}: {info['description']} (params: {params})")
    return "\n".join(lines)


def build_prompt() -> str:
    return SYSTEM_PROMPT.format(
        tools_description=build_tools_description(),
        user_facts=get_facts_for_prompt()
    )


def extract_and_execute_tools(response: str) -> tuple:
    """
    Extract tool calls from response, execute them, return results and clean response.
    """
    results = []
    
    # Find tool blocks
    tool_pattern = r'```tool\s*\n?(.*?)\n?```'
    matches = re.findall(tool_pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            tool_call = json.loads(match.strip())
            tool_name = tool_call.get("tool")
            params = tool_call.get("params", {})
            
            if tool_name in TOOLS:
                func = TOOLS[tool_name]["function"]
                result = func(**params) if params else func()
                results.append((tool_name, result))
                print(f"   🔧 {tool_name}: {result}")
        except json.JSONDecodeError as e:
            print(f"   ⚠️ Invalid tool JSON: {e}")
        except Exception as e:
            print(f"   ⚠️ Tool error: {e}")
    
    # Remove tool blocks from response
    clean = re.sub(tool_pattern, '', response, flags=re.DOTALL).strip()
    
    # Extract memories
    memory_pattern = r'\[REMEMBER:\s*([^\]]+)\]'
    for fact in re.findall(memory_pattern, clean):
        add_fact(fact.strip())
        print(f"   💾 Saved: {fact.strip()}")
    clean = re.sub(memory_pattern, '', clean).strip()
    
    # Extract voice changes
    voice_pattern = r'\[VOICE:\s*([^\]]+)\]'
    for voice in re.findall(voice_pattern, clean):
        result = set_voice(voice.strip())
        print(f"   🎤 {result}")
    clean = re.sub(voice_pattern, '', clean).strip()
    
    return results, clean


def print_header():
    print("\n" + "=" * 50)
    print("🤖 JARVIS v6 - Agentic AI Assistant")
    print("=" * 50)
    print("Just speak naturally! I'll understand and act.")
    print("Say 'pause' to stop, 'voices' to list voices")
    print("=" * 50 + "\n")


def main():
    print_header()
    check_api_keys()
    
    messages = []
    listening_paused = False
    
    # Greeting
    facts = get_all_facts()
    name = None
    for f in facts:
        if "name is" in f.get("fact", "").lower():
            name = f["fact"].split("name is")[-1].strip().split()[0].title()
            break
    
    greeting = f"Hey {name}! What can I do for you?" if name else "Hey! I'm Jarvis. What's your name?"
    print(f"🤖 {greeting}")
    speak(greeting)
    
    while True:
        try:
            print()
            
            if listening_paused:
                user_input = input("👤 (paused) Type or say 'resume': ").strip()
                if user_input.lower() in ['resume', 'continue', 'start listening']:
                    listening_paused = False
                    print("🎤 Resumed listening!")
                    speak("I'm listening again.")
                    continue
            else:
                # Voice input
                text = listen()
                if not text:
                    continue
                user_input = text
                print(f"👤 You: {user_input}")
            
            lower = user_input.lower().strip()
            
            # Quick commands
            if lower in ['quit', 'exit', 'goodbye', 'bye']:
                speak("Goodbye!")
                break
            
            if lower == 'memory':
                facts = get_all_facts()
                if facts:
                    print("\n📚 I remember:")
                    for f in facts:
                        print(f"   • {f['fact']}")
                else:
                    print("📚 No memories yet.")
                continue
            
            if lower == 'mute':
                toggle_speech()
                print(f"🔊 Speech {'ON' if is_speech_enabled() else 'OFF'}")
                continue
            
            if lower == 'voices':
                print(f"🎤 {list_voices()}")
                continue
            
            if lower.startswith('voice '):
                voice = lower.replace('voice ', '')
                result = set_voice(voice)
                print(f"🎤 {result}")
                speak(f"Voice changed to {voice}")
                continue
            
            # Add to conversation
            messages.append({"role": "user", "content": user_input})
            if len(messages) > 10:
                messages = messages[-10:]
            
            # Get LLM response
            response = chat(messages, build_prompt())
            
            # Execute any tools
            tool_results, clean_response = extract_and_execute_tools(response)
            
            # Check for pause command
            for tool_name, result in tool_results:
                if result == "PAUSE_LISTENING":
                    listening_paused = True
                    clean_response = "Okay, I'll stop listening. Say 'resume' when you need me."
            
            # If tools were executed but no verbal response, generate one
            if tool_results and not clean_response:
                last_tool, last_result = tool_results[-1]
                clean_response = last_result
            
            messages.append({"role": "assistant", "content": clean_response})
            
            # Output
            if clean_response:
                print(f"\n🤖 {clean_response}")
                speak(clean_response)
            
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
