#!/usr/bin/env python3
"""
JARVIS Smart LLM Router v5
With complexity detection and Gemini 1.5 Flash integration

Smart Routing Strategy:
- Simple queries: Free models (Groq → Cerebras → OpenRouter → Ollama)
- Complex queries: Gemini 1.5 Flash (if quota available) → Free models fallback
"""

import os
import re
import requests
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

# ============== API Keys ==============
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
GEMINI_KEYS = [k for k in [
    os.getenv("GEMINI_API_KEY_1", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
] if k]

# ============== Gemini Quota Tracking ==============
QUOTA_FILE = Path(__file__).parent.parent / "data" / "gemini_quota.json"
MAX_DAILY_REQUESTS = 40  # 2 accounts × 20 requests/day

def load_quota_tracker() -> dict:
    """Load Gemini quota tracking"""
    if not QUOTA_FILE.exists():
        return {"date": str(date.today()), "count": 0}
    
    try:
        import json
        with open(QUOTA_FILE, 'r') as f:
            data = json.load(f)
        # Reset if new day
        if data.get("date") != str(date.today()):
            data = {"date": str(date.today()), "count": 0}
        return data
    except:
        return {"date": str(date.today()), "count": 0}

def save_quota_tracker(data: dict):
    """Save Gemini quota tracking"""
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    import json
    with open(QUOTA_FILE, 'w') as f:
        json.dump(data, f)

def can_use_gemini() -> bool:
    """Check if Gemini can be used (quota available)"""
    tracker = load_quota_tracker()
    return tracker.get("count", 0) < MAX_DAILY_REQUESTS

def increment_gemini_usage():
    """Increment Gemini usage counter"""
    tracker = load_quota_tracker()
    tracker["count"] = tracker.get("count", 0) + 1
    save_quota_tracker(tracker)

# ============== Model Configs ==============
CEREBRAS_MODEL = "llama-3.3-70b"
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = "gemini-1.5-flash"

OPENROUTER_MODELS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-235b-a22b:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]

# ============== Complexity Detection ==============

def detect_complexity(user_message: str) -> str:
    """
    Detect query complexity using keyword/heuristic analysis.
    Returns 'simple' or 'complex'
    """
    text = user_message.lower().strip()
    
    # Complex indicators
    complex_patterns = [
        r'\b(code|program|function|debug|script|api|implement|build|create.*app|javascript|python|typescript|algorithm)\b',
        r'\b(explain|analyze|compare|why|how does|research|detailed|comprehensive|strategy|plan|step.*by.*step|breakdown)\b',
        r'\b(design|architecture|optimize|refactor|test|debugging|error handling)\b',
        r'\b(complex|complicated|sophisticated|advanced|technical)\b',
        r'\b(how to|tutorial|guide|walkthrough)\b',
        r'\b(problem|issue|bug|error|fix|solve|solution)\b',
    ]
    
    for pattern in complex_patterns:
        if re.search(pattern, text):
            return "complex"
    
    # Simple indicators (short, casual, quick questions)
    simple_patterns = [
        r'^(hi|hello|hey|good morning|good afternoon|good evening|thanks|thank you|bye|goodbye)',
        r'^\s*(what time|what\'s the time|current time|what day|what date)',
        r'^\s*(yes|no|ok|okay|sure|nope|yep)',
        r'^\s*(how are you|what\'s up|how\'s it going)',
    ]
    
    for pattern in simple_patterns:
        if re.match(pattern, text):
            return "simple"
    
    # Default based on length and structure
    if len(text.split()) <= 5 and '?' not in text:
        return "simple"
    
    return "simple"  # Default to simple to save Gemini quota


# ============== Provider Functions ==============

def call_gemini(messages: list, system_prompt: str) -> str:
    """Gemini 1.5 Flash - High quality for complex queries"""
    if not GEMINI_KEYS or not can_use_gemini():
        raise Exception("Gemini not available (no keys or quota exhausted)")
    
    print("🔷 Gemini 1.5 Flash...", end=" ", flush=True)
    
    # Try each key in rotation
    last_error = None
    for key in GEMINI_KEYS:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            
            # Convert messages to Gemini format
            model = genai.GenerativeModel(GEMINI_MODEL)
            
            # Build prompt with system instruction
            full_prompt = f"{system_prompt}\n\n"
            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    full_prompt += f"User: {content}\n\n"
                elif role == "assistant":
                    full_prompt += f"Assistant: {content}\n\n"
            full_prompt += "Assistant:"
            
            response = model.generate_content(
                full_prompt,
                generation_config={
                    "temperature": 0.7,
                    "max_output_tokens": 512,
                }
            )
            
            text = response.text.strip()
            if text:
                increment_gemini_usage()
                print("✓")
                return text
                
        except Exception as e:
            last_error = e
            continue
    
    raise Exception(f"Gemini failed: {last_error}" if last_error else "Gemini unavailable")


def call_groq(messages: list, system_prompt: str) -> str:
    """Groq - Very fast free tier"""
    if not GROQ_KEY:
        raise Exception("No Groq API key")
    
    print("⚡ Groq...", end=" ", flush=True)
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
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
            "max_tokens": 512,
        },
        timeout=15
    )
    
    if response.status_code == 200:
        text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if text:
            print("✓")
            return text.strip()
    
    raise Exception(f"Groq error: {response.status_code}")


def call_cerebras(messages: list, system_prompt: str) -> str:
    """Cerebras - Fast if available"""
    if not CEREBRAS_KEY:
        raise Exception("No Cerebras API key")
    
    print("🚀 Cerebras...", end=" ", flush=True)
    
    response = requests.post(
        "https://api.cerebras.ai/v1/chat/completions",
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
            "max_tokens": 512,
        },
        timeout=10
    )
    
    if response.status_code == 200:
        text = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        if text:
            print("✓")
            return text.strip()
    
    raise Exception(f"Cerebras error: {response.status_code}")


def call_openrouter(messages: list, system_prompt: str) -> str:
    """OpenRouter - Free models fallback"""
    if not OPENROUTER_KEY:
        raise Exception("No OpenRouter API key")
    
    for model in OPENROUTER_MODELS:
        print(f"🔶 OpenRouter ({model.split('/')[-1]})...", end=" ", flush=True)
        
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
                    "max_tokens": 512,
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
    
    try:
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
    except requests.exceptions.ConnectionError:
        raise Exception("Ollama not running (start with: ollama serve)")
    
    raise Exception("Ollama failed")


# ============== Main Router ==============

def chat(messages: list, system_prompt: str, offline_only: bool = False) -> str:
    """
    Smart router with complexity detection.
    Routes complex queries to Gemini 2.5 Flash, simple to free models.
    """
    if not messages:
        return "No messages provided."
    
    last_message = messages[-1].get("content", "") if messages else ""
    complexity = detect_complexity(last_message)
    
    providers = []
    
    if not offline_only:
        # Always prefer free providers first
        if GROQ_KEY:
            providers.append(("Groq", call_groq))
        if CEREBRAS_KEY:
            providers.append(("Cerebras", call_cerebras))
        if OPENROUTER_KEY:
            providers.append(("OpenRouter", call_openrouter))
        
        # Gemini reserved for complex/critical cases
        if complexity == "complex" and GEMINI_KEYS and can_use_gemini():
            providers.append(("Gemini", call_gemini))
    
    # Offline fallback (always available if running)
    providers.append(("Ollama", call_ollama))
    
    # Try providers in order
    last_error = None
    for name, fn in providers:
        try:
            return fn(messages, system_prompt)
        except Exception as e:
            last_error = e
            error_msg = str(e)[:80]
            print(f"✗ ({error_msg})")
            continue
    
    # All providers failed
    error_msg = str(last_error)[:100] if last_error else "Unknown error"
    return f"Sorry, I couldn't connect to any AI service. Last error: {error_msg}"


def check_api_keys():
    """Display configured API keys and quota"""
    tracker = load_quota_tracker()
    remaining = max(0, MAX_DAILY_REQUESTS - tracker.get("count", 0))
    
    print("\n🔑 API Configuration:")
    print(f"   Groq:        {'✓ ' + GROQ_KEY[:15] + '...' if GROQ_KEY else '✗ Not set'}")
    print(f"   Cerebras:    {'✓ ' + CEREBRAS_KEY[:15] + '...' if CEREBRAS_KEY else '✗ Not set'}")
    print(f"   OpenRouter:  {'✓ ' + OPENROUTER_KEY[:15] + '...' if OPENROUTER_KEY else '✗ Not set'}")
    print(f"   Gemini:      {len(GEMINI_KEYS)} key(s), {remaining}/{MAX_DAILY_REQUESTS} requests remaining today")
    print()
