#!/usr/bin/env python3
"""
🤖 JARVIS CLI - Terminal-Based AI Assistant

A simple, working terminal version of Jarvis that:
- Uses Gemini → OpenRouter → Ollama fallback
- Remembers facts about you
- Speaks responses aloud

Usage:
    python jarvis_cli.py
"""

import os
import sys
import re
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load .env file
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from {env_path}")
else:
    print(f"⚠️ No .env file found at {env_path}")
    print("   Create one with your API keys!")

from llm_router import chat, check_api_keys
from memory import get_facts_for_prompt, add_fact, get_all_facts, clear_memory, increment_conversation_count
from tts_simple import speak, list_voices, set_voice, set_rate


def build_system_prompt() -> str:
    """Build the system prompt with user facts"""
    facts = get_facts_for_prompt()
    
    return f"""You are Jarvis, a helpful, friendly, and efficient personal AI assistant.

## YOUR PERSONALITY
- Warm, professional, and occasionally witty
- Concise but thorough
- Proactive - anticipate follow-up needs

## USER MEMORY
{facts}

## INSTRUCTIONS
1. When the user tells you personal information (name, preferences, work, etc.), 
   you should remember it. Output a special tag: [SAVE_FACT: the fact to save]
2. Reference known facts naturally in conversation
3. Keep responses concise (2-4 sentences) since they will be spoken aloud
4. Be conversational and friendly

## EXAMPLES
User: "My name is Alex and I work at Google"
You: "Nice to meet you, Alex! Working at Google must be exciting. What do you do there? [SAVE_FACT: User's name is Alex] [SAVE_FACT: User works at Google]"

User: "What's my name?"
You: "Your name is Alex! You told me earlier. Is there anything I can help you with today?"

Remember to be helpful and conversational!"""


def extract_and_save_facts(response: str) -> str:
    """Extract [SAVE_FACT: ...] tags from response and save them"""
    # Find all SAVE_FACT tags
    pattern = r'\[SAVE_FACT:\s*([^\]]+)\]'
    matches = re.findall(pattern, response)
    
    for fact in matches:
        add_fact(fact.strip())
    
    # Remove the tags from the response
    clean_response = re.sub(pattern, '', response).strip()
    # Clean up extra whitespace
    clean_response = re.sub(r'\s+', ' ', clean_response).strip()
    
    return clean_response


def print_header():
    """Print welcome header"""
    print("\n" + "=" * 60)
    print("🤖 JARVIS CLI - Terminal AI Assistant")
    print("=" * 60)
    print("\nCommands:")
    print("  Type your message and press Enter to chat")
    print("  'memory'  - Show what I remember about you")
    print("  'clear'   - Clear my memory")
    print("  'voices'  - List available TTS voices")
    print("  'voice N' - Set voice to index N")
    print("  'mute'    - Toggle speech on/off")
    print("  'keys'    - Show API key status")
    print("  'quit'    - Exit Jarvis")
    print("=" * 60 + "\n")


def main():
    """Main CLI loop"""
    print_header()
    check_api_keys()
    
    # Conversation state
    messages = []
    speech_enabled = True
    conversation_num = increment_conversation_count()
    
    print(f"📝 This is conversation #{conversation_num}")
    print("🎤 Speech is ON (say 'mute' to toggle)\n")
    
    # Initial greeting
    facts = get_all_facts()
    if facts:
        # Check if we know the user's name
        name = None
        for f in facts:
            if "name is" in f["fact"].lower():
                name = f["fact"].split("name is")[-1].strip().split()[0]
                break
        
        if name:
            greeting = f"Welcome back, {name}! How can I help you today?"
        else:
            greeting = "Welcome back! I remember you. How can I help today?"
    else:
        greeting = "Hello! I'm Jarvis, your AI assistant. What's your name?"
    
    print(f"🤖 Jarvis: {greeting}")
    if speech_enabled:
        speak(greeting)
    print()
    
    while True:
        try:
            # Get user input
            user_input = input("👤 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() == 'quit':
                farewell = "Goodbye! Have a great day!"
                print(f"\n🤖 Jarvis: {farewell}")
                if speech_enabled:
                    speak(farewell)
                break
            
            if user_input.lower() == 'memory':
                facts = get_all_facts()
                if facts:
                    print("\n📚 Things I remember:")
                    for f in facts:
                        print(f"   - {f['fact']}")
                else:
                    print("\n📚 I don't have any memories yet.")
                print()
                continue
            
            if user_input.lower() == 'clear':
                clear_memory()
                messages = []  # Clear conversation too
                print()
                continue
            
            if user_input.lower() == 'voices':
                list_voices()
                print()
                continue
            
            if user_input.lower().startswith('voice '):
                try:
                    idx = int(user_input.split()[1])
                    set_voice(idx)
                except:
                    print("⚠️ Usage: voice <number>")
                print()
                continue
            
            if user_input.lower() == 'mute':
                speech_enabled = not speech_enabled
                status = "ON" if speech_enabled else "OFF"
                print(f"🔊 Speech is now {status}")
                print()
                continue
            
            if user_input.lower() == 'keys':
                check_api_keys()
                continue
            
            # Add to conversation history
            messages.append({"role": "user", "content": user_input})
            
            # Keep conversation history manageable (last 10 exchanges)
            if len(messages) > 20:
                messages = messages[-20:]
            
            # Get AI response
            print("\n🤔 Thinking...")
            system_prompt = build_system_prompt()
            response = chat(messages, system_prompt)
            
            # Extract and save any facts
            clean_response = extract_and_save_facts(response)
            
            # Add to history
            messages.append({"role": "assistant", "content": clean_response})
            
            # Display response
            print(f"\n🤖 Jarvis: {clean_response}")
            
            # Speak response
            if speech_enabled:
                speak(clean_response)
            
            print()
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print()


if __name__ == "__main__":
    main()
