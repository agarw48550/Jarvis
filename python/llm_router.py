#!/usr/bin/env python3
"""
LLM Router - Gemini → OpenRouter → Ollama fallback chain
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY_1", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]  # Remove empty keys

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Track which Gemini key to use (rotate on failure)
current_gemini_index = 0

# OpenRouter free models
OPENROUTER_MODELS = [
    "google/gemini-2.0-flash-exp:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


def classify_complexity(message: str) -> str:
    """Classify if message needs simple or complex model"""
    message_lower = message.lower()
    
    # Complex indicators
    complex_keywords = [
        "explain", "analyze", "compare", "why", "how does",
        "code", "program", "debug", "implement", "build",
        "research", "detailed", "comprehensive", "step by step"
    ]
    
    if any(kw in message_lower for kw in complex_keywords) or len(message) > 200:
        return "complex"
    return "simple"


def call_gemini(messages: list, system_prompt: str) -> str:
    """Call Gemini API"""
    global current_gemini_index
    
    if not GEMINI_KEYS:
        raise Exception("No Gemini API keys configured")
    
    # Try each key
    for i in range(len(GEMINI_KEYS)):
        key_index = (current_gemini_index + i) % len(GEMINI_KEYS)
        api_key = GEMINI_KEYS[key_index]
        
        # Choose model based on complexity
        last_message = messages[-1]["content"] if messages else ""
        complexity = classify_complexity(last_message)
        model = "gemini-2.0-flash" if complexity == "simple" else "gemini-2.0-flash"
        
        print(f"🔷 Trying Gemini ({model}) with key {key_index + 1}...")
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_messages.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": gemini_messages,
                "generationConfig": {
                    "temperature": 0.7,
                    "maxOutputTokens": 1024
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                if text:
                    print(f"✅ Gemini response received!")
                    return text
            else:
                error_msg = response.json().get("error", {}).get("message", response.text)
                print(f"⚠️ Gemini key {key_index + 1} error: {error_msg}")
                current_gemini_index = (key_index + 1) % len(GEMINI_KEYS)
                
        except Exception as e:
            print(f"⚠️ Gemini key {key_index + 1} failed: {e}")
            current_gemini_index = (key_index + 1) % len(GEMINI_KEYS)
    
    raise Exception("All Gemini keys failed")


def call_openrouter(messages: list, system_prompt: str) -> str:
    """Call OpenRouter API with free models"""
    if not OPENROUTER_KEY:
        raise Exception("No OpenRouter API key configured")
    
    for model in OPENROUTER_MODELS:
        print(f"🔶 Trying OpenRouter ({model})...")
        
        try:
            url = "https://openrouter.ai/api/v1/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://jarvis-assistant.local",
                "X-Title": "Jarvis CLI"
            }
            
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    *messages
                ]
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                if text:
                    print(f"✅ OpenRouter response received!")
                    return text
            else:
                print(f"⚠️ OpenRouter {model} error: {response.text[:100]}")
                
        except Exception as e:
            print(f"⚠️ OpenRouter {model} failed: {e}")
    
    raise Exception("All OpenRouter models failed")


def call_ollama(messages: list, system_prompt: str) -> str:
    """Call local Ollama as final fallback"""
    print("🟢 Trying Ollama (local)...")
    
    try:
        url = "http://localhost:11434/api/chat"
        
        payload = {
            "model": "tinyllama",
            "messages": [
                {"role": "system", "content": system_prompt},
                *messages
            ],
            "stream": False
        }
        
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            text = data.get("message", {}).get("content", "")
            if text:
                print(f"✅ Ollama response received!")
                return text
                
    except Exception as e:
        print(f"⚠️ Ollama failed: {e}")
    
    raise Exception("Ollama not available")


def chat(messages: list, system_prompt: str) -> str:
    """
    Route chat to available LLM provider.
    Tries: Gemini → OpenRouter → Ollama
    """
    providers = [
        ("Gemini", call_gemini),
        ("OpenRouter", call_openrouter),
        ("Ollama", call_ollama),
    ]
    
    last_error = None
    
    for name, provider_fn in providers:
        try:
            return provider_fn(messages, system_prompt)
        except Exception as e:
            last_error = e
            print(f"❌ {name} failed, trying next...")
    
    return f"I'm sorry, I couldn't connect to any AI service. Error: {last_error}"


def check_api_keys():
    """Check which API keys are configured"""
    print("\n🔑 API Key Status:")
    print(f"   Gemini keys: {len(GEMINI_KEYS)} configured")
    for i, key in enumerate(GEMINI_KEYS):
        masked = key[:10] + "..." + key[-4:] if len(key) > 14 else "***"
        print(f"      Key {i+1}: {masked}")
    
    if OPENROUTER_KEY:
        masked = OPENROUTER_KEY[:10] + "..." + OPENROUTER_KEY[-4:]
        print(f"   OpenRouter: {masked}")
    else:
        print("   OpenRouter: Not configured")
    
    print()
