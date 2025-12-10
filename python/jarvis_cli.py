#!/usr/bin/env python3
"""
🤖 JARVIS v8 - Complete Agentic AI Assistant
Fixed: Pause bug, Multilingual, Smart search
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
from memory import get_facts_for_prompt, add_fact, get_all_facts
from tts_simple import speak, toggle_speech, is_speech_enabled, set_voice, list_voices, VOICES
from stt_cloud import listen
from actions import TOOLS

# ============== System Prompt ==============

SYSTEM_PROMPT = """You are Jarvis, an intelligent multilingual voice assistant.

## CRITICAL RULES
1. ALWAYS use tools when user asks to DO something
2. Keep responses SHORT (1-2 sentences)
3. MATCH THE USER'S LANGUAGE - if they speak Chinese, respond in Chinese
4. After search_web or search_news, SUMMARIZE the results in 1-2 clear sentences
5. Be conversational and natural

## LANGUAGE EXAMPLES
- User: "你好" → Respond in Chinese: "你好！有什么我可以帮你的吗？"
- User: "Hola" → Respond in Spanish: "¡Hola! ¿En qué puedo ayudarte?"
- User: "Bonjour" → Respond in French: "Bonjour! Comment puis-je vous aider?"

## AVAILABLE TOOLS
{tools_description}

## HOW TO USE TOOLS
```tool
{{"tool": "tool_name", "params": {{"key": "value"}}}}
```

## SEARCH HANDLING
When you get search results, SUMMARIZE them naturally. Don't read raw snippets.
Example: "I found that the best pizza places near you are Domino's, Pizza Hut, and a local spot called Mario's."

## MEMORY
Save facts: [REMEMBER: fact here]
{user_facts}

## KEY EXAMPLES

Weather:
```tool
{{"tool": "get_weather", "params": {{"city": "Tokyo"}}}}
```

Search (always summarize after):
```tool
{{"tool": "search_web", "params": {{"query": "best pizza Singapore"}}}}
```
Then say: "The top pizza places in Singapore are..."

News:
```tool
{{"tool": "search_news", "params": {{"query": "technology"}}}}
```

Reminders:
```tool
{{"tool": "get_reminders", "params": {{}}}}
```

Timer:
```tool
{{"tool": "set_timer", "params": {{"minutes": 5, "label": "Tea"}}}}
```

Email:
```tool
{{"tool": "send_email", "params": {{"to": "email@example.com", "subject": "Hello", "body": "Message here"}}}}
```

Calendar:
```tool
{{"tool": "get_calendar_events", "params": {{}}}}
```

Exit (goodbye/bye/quit):
```tool
{{"tool": "exit_jarvis", "params": {{}}}}
```

Pause (only when explicitly asked):
```tool
{{"tool": "pause_listening", "params": {{}}}}
```

IMPORTANT: Only use pause_listening when user EXPLICITLY says "pause", "stop listening", or "wait". NOT for words like "please" or normal conversation."""


def build_tools_description() -> str:
    lines = []
    for name, info in TOOLS.items():
        params = ", ".join(f"{k}: {v}" for k, v in info["parameters"].items()) or "none"
        lines.append(f"- {name}: {info['description']}")
    return "\n".join(lines)


def build_prompt() -> str:
    return SYSTEM_PROMPT.format(
        tools_description=build_tools_description(),
        user_facts=get_facts_for_prompt()
    )


def extract_and_execute_tools(response: str) -> tuple:
    """Extract and execute tool calls, return results and clean response"""
    results = []
    
    # Find tool blocks
    pattern = r'```tool\s*\n?(.*?)\n?```'
    matches = re.findall(pattern, response, re.DOTALL)
    
    for match in matches:
        try:
            tool_call = json.loads(match.strip())
            tool_name = tool_call.get("tool")
            params = tool_call.get("params", {})
            
            if tool_name and tool_name in TOOLS:
                func = TOOLS[tool_name]["function"]
                params = {k: v for k, v in params.items() if v is not None}
                result = func(**params) if params else func()
                results.append((tool_name, result))
                # Shorter output for cleanliness
                display = result[:80] + "..." if len(result) > 80 else result
                print(f"   🔧 {tool_name}: {display}")
        except json.JSONDecodeError:
            pass
        except Exception as e:
            print(f"   ⚠️ Tool error: {e}")
    
    # Clean response
    clean = re.sub(pattern, '', response, flags=re.DOTALL).strip()
    
    # Extract memories
    for fact in re.findall(r'\[REMEMBER:\s*([^\]]+)\]', clean):
        add_fact(fact.strip())
        print(f"   💾 Saved: {fact.strip()}")
    clean = re.sub(r'\[REMEMBER:\s*[^\]]+\]', '', clean).strip()
    
    # Extract voice changes
    for voice in re.findall(r'\[VOICE:\s*([^\]]+)\]', clean):
        set_voice(voice.strip())
    clean = re.sub(r'\[VOICE:\s*[^\]]+\]', '', clean).strip()
    
    return results, re.sub(r'\s+', ' ', clean).strip()


def print_header():
    print("\n" + "=" * 55)
    print("🤖 JARVIS v8 - Agentic AI Assistant")
    print("=" * 55)
    print("Speak naturally in any language!")
    print("Commands: 'pause' 'voices' 'memory' 'goodbye'")
    print("=" * 55 + "\n")


def main():
    print_header()
    check_api_keys()
    
    messages = []
    paused = False  # Fixed: properly scoped
    
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
            
            if paused:
                user_input = input("⏸️ (paused) Say 'resume': ").strip()
                if user_input.lower() in ['resume', 'continue', 'start', '']:
                    paused = False
                    print("🎤 Listening resumed!")
                    speak("I'm listening again!")
                    continue
                elif user_input.lower() not in ['resume', 'continue']:
                    # Allow commands while paused
                    pass
                else:
                    continue
            else:
                text = listen()
                if not text:
                    continue
                user_input = text
                print(f"👤 You: {user_input}")
            
            lower = user_input.lower().strip()
            
            # Quick commands
            if lower == 'voices':
                print(f"🎤 {list_voices()}")
                continue
            
            if lower.startswith('voice '):
                set_voice(lower.replace('voice ', ''))
                continue
            
            if lower == 'memory':
                facts = get_all_facts()
                if facts:
                    for f in facts:
                        print(f"   • {f['fact']}")
                else:
                    print("   No memories yet.")
                continue
            
            if lower == 'mute':
                toggle_speech()
                print(f"🔊 Speech {'ON' if is_speech_enabled() else 'OFF'}")
                continue
            
            # Build conversation
            messages.append({"role": "user", "content": user_input})
            if len(messages) > 20:
                messages = messages[-20:]
            
            # Get response
            response = chat(messages, build_prompt())
            
            # Execute tools
            tool_results, clean_response = extract_and_execute_tools(response)
            
            # Handle control signals
            should_exit = False
            for tool_name, result in tool_results:
                if result == "__PAUSE__":
                    paused = True
                    clean_response = "Okay, I'll wait. Say 'resume' when ready."
                elif result == "__EXIT__":
                    should_exit = True
                    clean_response = "Goodbye! Have a great day!"
            
            # Use tool result if no text response
            if tool_results and not clean_response:
                _, last_result = tool_results[-1]
                if not last_result.startswith("__"):
                    clean_response = last_result
            
            # Update history
            if clean_response:
                messages.append({"role": "assistant", "content": clean_response})
                print(f"\n🤖 {clean_response}")
                speak(clean_response)
            
            if should_exit:
                break
            
        except KeyboardInterrupt:
            print("\n\n👋 Bye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    main()
