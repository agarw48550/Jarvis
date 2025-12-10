#!/usr/bin/env python3
"""
🤖 JARVIS v7 - Complete Agentic AI Assistant
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
from tts_simple import speak, toggle_speech, is_speech_enabled, set_voice, list_voices, VOICES
from stt_cloud import listen
from actions import TOOLS

# ============== System Prompt ==============

SYSTEM_PROMPT = """You are Jarvis, an intelligent voice assistant that TAKES ACTION.

## CRITICAL RULES
1. When user asks you to DO something, USE A TOOL - don't just say you'll do it
2. Keep responses SHORT (1-2 sentences max)
3. Be conversational and natural
4. Match the user's language (if they speak Spanish, respond in Spanish)

## AVAILABLE TOOLS
{tools_description}

## HOW TO USE TOOLS
Output a JSON code block when you need to perform an action:
```tool
{{"tool": "tool_name", "params": {{"param1": "value1"}}}}
```

## MEMORY
When user shares personal info, output: [REMEMBER: fact here]
{user_facts}

## VOICE CONTROL
To change voice: [VOICE: calum/cillian/atlas/arista]
Available voices: {voices}

## IMPORTANT TOOL USAGE EXAMPLES

"What's the weather in Tokyo?" →
```tool
{{"tool": "get_weather", "params": {{"city": "Tokyo"}}}}
```

"Search for best restaurants" →
```tool
{{"tool": "search_web", "params": {{"query": "best restaurants"}}}}
```

"Find pizza near me" →
```tool
{{"tool": "search_web", "params": {{"query": "pizza near me"}}}}
```

"Set volume to 50" OR "Volume 50 percent" →
```tool
{{"tool": "set_volume", "params": {{"level": 50}}}}
```

"What are my reminders?" OR "Do I have any reminders?" →
```tool
{{"tool": "get_reminders", "params": {{}}}}
```

"Stop listening" OR "Pause" OR "Hold on" →
```tool
{{"tool": "pause_listening", "params": {{}}}}
```

"Goodbye" OR "Quit" OR "Exit" OR "Bye" →
```tool
{{"tool": "exit_jarvis", "params": {{}}}}
```

"Take a screenshot" →
```tool
{{"tool": "take_screenshot", "params": {{}}}}
```

"What's my battery?" →
```tool
{{"tool": "get_battery", "params": {{}}}}
```

ALWAYS USE TOOLS FOR ACTIONS. Never just describe what you would do."""


def build_tools_description() -> str:
    lines = []
    for name, info in TOOLS.items():
        params = ", ".join(f"{k}: {v}" for k, v in info["parameters"].items()) or "none"
        lines.append(f"- {name}: {info['description']} ({params})")
    return "\n".join(lines)


def build_prompt() -> str:
    return SYSTEM_PROMPT.format(
        tools_description=build_tools_description(),
        user_facts=get_facts_for_prompt(),
        voices=", ".join(VOICES.keys())
    )


def extract_and_execute_tools(response: str) -> tuple:
    """Extract tool calls, execute them, return results and clean response"""
    results = []
    
    # Find tool blocks (multiple patterns)
    patterns = [
        r'```tool\s*\n?(.*?)\n?```',
        r'```json\s*\n?(.*?)\n?```',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, response, re.DOTALL)
        for match in matches:
            try:
                tool_call = json.loads(match.strip())
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})
                
                if tool_name and tool_name in TOOLS:
                    func = TOOLS[tool_name]["function"]
                    # Filter out None params
                    params = {k: v for k, v in params.items() if v is not None}
                    result = func(**params) if params else func()
                    results.append((tool_name, result))
                    print(f"   🔧 {tool_name}: {result[:100]}...")
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"   ⚠️ Tool error: {e}")
    
    # Remove tool blocks
    clean = response
    for pattern in patterns:
        clean = re.sub(pattern, '', clean, flags=re.DOTALL)
    clean = clean.strip()
    
    # Extract memories
    memory_pattern = r'\[REMEMBER:\s*([^\]]+)\]'
    for fact in re.findall(memory_pattern, clean):
        add_fact(fact.strip())
        print(f"   💾 Remembered: {fact.strip()}")
    clean = re.sub(memory_pattern, '', clean).strip()
    
    # Extract voice changes
    voice_pattern = r'\[VOICE:\s*([^\]]+)\]'
    for voice in re.findall(voice_pattern, clean):
        result = set_voice(voice.strip())
        print(f"   🎤 {result}")
    clean = re.sub(voice_pattern, '', clean).strip()
    
    # Clean extra whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    
    return results, clean


def print_header():
    print("\n" + "=" * 55)
    print("🤖 JARVIS v7 - Agentic AI Assistant")
    print("=" * 55)
    print("Just speak naturally! I'll understand and act.")
    print("Say 'pause' to stop, 'goodbye' to exit, 'voices' for voice options")
    print("=" * 55 + "\n")


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
            name = f["fact"].lower().split("name is")[-1].strip().split()[0].title()
            break
    
    greeting = f"Hey {name}! What can I do for you?" if name else "Hey! I'm Jarvis. What's your name?"
    print(f"🤖 {greeting}")
    speak(greeting)
    
    while True:
        try:
            print()
            
            # Handle paused state
            if listening_paused:
                user_input = input("⏸️ (paused) Type 'resume' or press Enter to listen: ").strip()
                if not user_input:
                    text = listen()
                    if text:
                        user_input = text
                        print(f"👤 You: {user_input}")
                
                if user_input.lower() in ['resume', 'continue', 'start', 'listen', 'unpause']:
                    listening_paused = False
                    msg = "I'm listening again!"
                    print(f"🤖 {msg}")
                    speak(msg)
                    continue
            else:
                # Normal voice input
                text = listen()
                if not text:
                    continue
                user_input = text
                print(f"👤 You: {user_input}")
            
            lower = user_input.lower().strip()
            
            # Quick local commands (don't need LLM)
            if lower == 'voices':
                msg = list_voices()
                print(f"🎤 {msg}")
                speak(msg)
                continue
            
            if lower.startswith('voice '):
                voice = lower.replace('voice ', '').strip()
                result = set_voice(voice)
                print(f"🎤 {result}")
                speak(f"Voice changed to {voice}")
                continue
            
            if lower == 'memory':
                facts = get_all_facts()
                if facts:
                    print("\n📚 I remember:")
                    for f in facts:
                        print(f"   • {f['fact']}")
                    speak(f"I remember {len(facts)} things about you.")
                else:
                    print("📚 No memories yet.")
                    speak("I don't have any memories yet.")
                continue
            
            if lower == 'mute':
                enabled = toggle_speech()
                print(f"🔊 Speech {'ON' if enabled else 'OFF'}")
                continue
            
            # Add to conversation (keep more history for context)
            messages.append({"role": "user", "content": user_input})
            if len(messages) > 20:  # Keep last 20 messages for better context
                messages = messages[-20:]
            
            # Get LLM response
            response = chat(messages, build_prompt())
            
            # Execute tools
            tool_results, clean_response = extract_and_execute_tools(response)
            
            # Check for control signals
            should_exit = False
            for tool_name, result in tool_results:
                if result == "__PAUSE__":
                    listening_paused = True
                    clean_response = "Okay, I'll wait. Say 'resume' when you need me."
                elif result == "__EXIT__":
                    should_exit = True
                    clean_response = "Goodbye! Have a great day!"
            
            # If tools executed but no verbal response, use tool result
            if tool_results and not clean_response:
                last_tool, last_result = tool_results[-1]
                if not last_result.startswith("__"):
                    clean_response = last_result
            
            # Add to history
            if clean_response:
                messages.append({"role": "assistant", "content": clean_response})
            
            # Output
            if clean_response:
                print(f"\n🤖 {clean_response}")
                speak(clean_response)
            
            # Exit if requested
            if should_exit:
                break
            
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()
