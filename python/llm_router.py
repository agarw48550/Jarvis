#!/usr/bin/env python3
"""
JARVIS Smart LLM Router v4
Optimized for speed and natural conversation

Provider Priority:
1. Cerebras (2,600 tok/s) - Fastest
2. Groq (460 tok/s) - Very fast
3. OpenRouter - Free models
4. Gemini - Limited quota
5. Ollama - Offline fallback
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

# ============== API Keys ==============
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_KEYS = [k for k in [
    os.getenv("GEMINI_API_KEY_1", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
] if k]

# ============== Model Configs ==============
# Cerebras - Fastest (2,600 tok/s)
CEREBRAS_MODEL = "llama-3.3-70b"

# Groq - Very Fast (460 tok/s)
GROQ_MODEL = "llama-3.3-70b-versatile"

# OpenRouter - Free models
OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# ============== Provider Functions ==============

def call_cerebras(messages: list, system_prompt: str) -> str:
    """Cerebras - FASTEST at ~2,600 tokens/sec"""
    if not CEREBRAS_KEY:
        raise Exception("No Cerebras API key")
    
    print("🚀 Cerebras (fastest)...", end=" ", flush=True)
    
    url = "https://api.cerebras.ai/v1/chat/completions"
    
    response = requests.post(url,
        headers={
            "Authorization": f"Bearer {CEREBRAS_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": CEREBRAS_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "temperature": 0.7,
            "max_tokens": 150,  # Short responses for conversation
        },
        timeout=10
    )
    
    if response.status_code == 200:
        text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if text:
            print("✓")
            return text.strip()
    
    raise Exception(f"Cerebras error: {response.text[:100]}")


def call_groq(messages: list, system_prompt: str) -> str:
    """Groq - Very fast at ~460 tokens/sec"""
    if not GROQ_KEY:
        raise Exception("No Groq API key")
    
    print("⚡ Groq...", end=" ", flush=True)
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    
    response = requests.post(url,
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "temperature": 0.7,
            "max_tokens": 150,
        },
        timeout=15
    )
    
    if response.status_code == 200:
        text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if text:
            print("✓")
            return text.strip()
    
    raise Exception(f"Groq error: {response.text[:100]}")


def call_openrouter(messages: list, system_prompt: str) -> str:
    """OpenRouter - Free models fallback"""
    if not OPENROUTER_KEY:
        raise Exception("No OpenRouter API key")
    
    for model in OPENROUTER_MODELS:
        print(f"🔶 OpenRouter...", end=" ", flush=True)
        
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        *messages
                    ],
                    "max_tokens": 150,
                },
                timeout=30
            )
            
            if response.status_code == 200:
                text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                if text:
                    print("✓")
                    return text.strip()
        except:
            continue
    
    raise Exception("OpenRouter failed")


def call_ollama(messages: list, system_prompt: str) -> str:
    """Ollama - Local offline fallback"""
    print("🟢 Ollama (local)...", end=" ", flush=True)
    
    response = requests.post(
        "http://localhost:11434/api/chat",
        json={
            "model": "llama3.2",
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "stream": False,
        },
        timeout=60
    )
    
    if response.status_code == 200:
        text = response.json().get("message", {}).get("content", "")
        if text:
            print("✓")
            return text.strip()
    
    raise Exception("Ollama failed")


# ============== Main Router ==============

def chat(messages: list, system_prompt: str) -> str:
    """
    Smart router - tries fastest providers first.
    Optimized for conversational speed.
    """
    
    # Priority order: Cerebras > Groq > OpenRouter > Ollama
    providers = []
    
    if CEREBRAS_KEY:
        providers.append(("Cerebras", call_cerebras))
    if GROQ_KEY:
        providers.append(("Groq", call_groq))
    if OPENROUTER_KEY:
        providers.append(("OpenRouter", call_openrouter))
    providers.append(("Ollama", call_ollama))
    
    for name, fn in providers:
        try:
            return fn(messages, system_prompt)
        except Exception as e:
            print(f"✗ ({e})")
            continue
    
    return "Sorry, I couldn't connect to any AI service."


def check_api_keys():
    """Display configured API keys"""
    print("\n🔑 API Configuration:")
    print(f"   Cerebras:    {'✓ ' + CEREBRAS_KEY[:15] + '...' if CEREBRAS_KEY else '✗ Not set'}")
    print(f"   Groq:        {'✓ ' + GROQ_KEY[:15] + '...' if GROQ_KEY else '✗ Not set'}")
    print(f"   OpenRouter:  {'✓ ' + OPENROUTER_KEY[:15] + '...' if OPENROUTER_KEY else '✗ Not set'}")
    print(f"   Gemini:      {len(GEMINI_KEYS)} key(s)")
    print()


def detect_action(user_input: str) -> tuple:
    """
    Detect if user wants to perform an action.
    Returns (action_name, params) or (None, None)
    """
    text = user_input.lower().strip()
    
    # === Time ===
    if any(phrase in text for phrase in [
        "what time", "what's the time", "current time",
        "what is the time", "tell me the time"
    ]):
        return ("time", {})
    
    # === Web Search ===
    search_triggers = [
        "search for ", "search ", "google ", "look up ",
        "find information about ", "look for "
    ]
    for trigger in search_triggers:
        if text.startswith(trigger):
            query = user_input[len(trigger):].strip()
            if query:
                return ("search", {"query": query})
    
    # Also catch "search X" patterns
    if "search" in text and "for" not in text:
        words = text.split("search", 1)
        if len(words) > 1 and words[1].strip():
            return ("search", {"query": words[1].strip()})
    
    # === Open App ===
    open_triggers = ["open ", "launch ", "start "]
    for trigger in open_triggers:
        if text.startswith(trigger):
            app = user_input[len(trigger):].strip().rstrip('.')
            if app:
                return ("open", {"app_name": app})
    
    # === Reminders ===
    if any(phrase in text for phrase in ["remind me", "set a reminder", "remember to"]):
        # Extract the reminder text
        for prefix in ["remind me to ", "remind me ", "remember to ", "set a reminder to ", "set a reminder "]:
            if text.startswith(prefix):
                reminder_text = user_input[len(prefix):].strip()
                if reminder_text:
                    return ("remind", {"text": reminder_text})
        return ("remind", {"text": user_input})
    
    if text in ["reminders", "my reminders", "show reminders", "list reminders", "what are my reminders"]:
        return ("reminders", {})
    
    if text in ["clear reminders", "delete reminders", "remove reminders"]:
        return ("clear_reminders", {})
    
    # === Volume ===
    if any(phrase in text for phrase in ["volume up", "turn up the volume", "louder", "increase volume"]):
        return ("volume", {"action": "up"})
    
    if any(phrase in text for phrase in ["volume down", "turn down the volume", "quieter", "decrease volume", "lower volume"]):
        return ("volume", {"action": "down"})
    
    if any(phrase in text for phrase in ["mute", "silence", "quiet"]) and "unmute" not in text:
        return ("volume", {"action": "mute"})
    
    if "unmute" in text:
        return ("volume", {"action": "unmute"})
    
    if "max volume" in text or "maximum volume" in text:
        return ("volume", {"action": "max"})
    
    return (None, None)


