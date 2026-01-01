#!/usr/bin/env python3
"""
JARVIS Smart LLM Router v5
With complexity detection and Gemini 1.5 Flash integration

Smart Routing Strategy:
- Simple queries: Free models (Groq → Cerebras → OpenRouter → Ollama)
- Complex queries: Gemini 1.5 Flash (if quota available) → Free models fallback
"""

import json
import threading
import os
import re
import requests
import random
import asyncio
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional
from google import genai
from google.genai import types

from core.config import API_KEYS, MODELS, QUOTAS, SYSTEM_PROMPT

# ============== API Keys ==============
CEREBRAS_KEY = API_KEYS.cerebras_key
GROQ_KEY = API_KEYS.groq_key
OPENROUTER_KEY = API_KEYS.openrouter_key
GEMINI_KEYS = API_KEYS.gemini_keys

# ============== Gemini Quota Tracking ==============
QUOTA_FILE = Path(__file__).parent.parent / "data" / "gemini_quota.json"
MAX_DAILY_REQUESTS = QUOTAS.gemini_daily_limit
quota_lock = threading.Lock()

def load_quota_tracker() -> dict:
    """Load Gemini quota tracking"""
    if not QUOTA_FILE.exists():
        return {"date": str(date.today()), "count": 0}
    
    try:
        with open(QUOTA_FILE, 'r') as f:
            data = json.load(f)
        # Reset if new day
        if data.get("date") != str(date.today()):
            data = {"date": str(date.today()), "count": 0}
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": str(date.today()), "count": 0}

def save_quota_tracker(data: dict):
    """Save Gemini quota tracking"""
    QUOTA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_FILE, 'w') as f:
        json.dump(data, f)

def can_use_gemini() -> bool:
    """Check if Gemini can be used (quota available)"""
    with quota_lock:
        tracker = load_quota_tracker()
        return tracker.get("count", 0) < MAX_DAILY_REQUESTS

def increment_gemini_usage():
    """Increment Gemini usage counter"""
    with quota_lock:
        tracker = load_quota_tracker()
        tracker["count"] = tracker.get("count", 0) + 1
        save_quota_tracker(tracker)

# ============== Model Configs ==============
CEREBRAS_MODEL = MODELS.cerebras_model
GROQ_MODEL = MODELS.groq_model
GEMINI_MODEL = MODELS.gemini_text_model

OPENROUTER_MODELS = MODELS.openrouter_models

# ============== Complexity Detection ==============

# ============== Optimization Strategy ==============

def classify_task(user_message: str) -> str:
    """Classify the task type from user message"""
    msg = user_message.lower()
    
    patterns = {
        'code': r'(code|program|function|debug|script|implement|build|python|javascript|typescript|html|css)',
        'math': r'(calculate|compute|solve|equation|math|formula|\d+\s*[+\-*/]\s*\d+)',
        'creative': r'(write|story|poem|creative|imagine|describe.*scene|essay|blog)',
        'search': r'(search|find|look up|what is|who is|when did|current|news)',
        'tool': r'(set.*timer|reminder|open.*app|play.*music|volume|weather)',
    }
    
    for task_type, pattern in patterns.items():
        if re.search(pattern, msg):
            return task_type
    
    return 'chat'

def select_providers(task_type: str) -> list:
    """Select optimal provider chain for the task"""
    # Map string names to function objects
    # We use string lookups to avoid circular dependency or declaration issues
    # But since functions are defined below, we can referencing them directly? 
    # Python allows referencing functions defined later if we are inside a function call.
    # But for cleaner code, let's use a lookup at runtime.
    
    provider_map = {
        'code': [call_cerebras, call_groq, call_gemini],
        'chat': [call_groq, call_cerebras, call_gemini],
        'search': [call_groq, call_cerebras],
        'math': [call_cerebras, call_groq, call_gemini],
        'creative': [call_gemini, call_openrouter, call_groq],
        'tool': [call_groq, call_cerebras],
    }
    
    return provider_map.get(task_type, [call_groq, call_cerebras])

async def async_call_provider(provider_fn, messages, system_prompt):
    """Wrapper to run sync provider functions in thread pool"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, provider_fn, messages, system_prompt)

async def chat_async(messages: list, system_prompt: str) -> str:
    """Race multiple providers for speed"""
    if not messages:
        return "No messages."
        
    last_content = messages[-1].get("content", "")
    task_type = classify_task(last_content)
    # print(f"🧠 Task Type: {task_type}") # Debug
    
    providers = select_providers(task_type)
    
    # 🏎️ RACE CONDITION: For chat/tool, race the top 2
    if task_type in ['chat', 'tool'] and len(providers) >= 2:
        tasks = []
        for p in providers[:2]:
            tasks.append(asyncio.create_task(async_call_provider(p, messages, system_prompt)))
            
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        
        # Cancel losers
        for t in pending:
            t.cancel()
            
        # Return winner
        for t in done:
            try:
                result = t.result()
                if result: return result
            except:
                continue
    
    # Fallback or sequential
    for p in providers:
        try:
            return await async_call_provider(p, messages, system_prompt)
        except:
            continue
            
    return "All AI services failed."


# ============== Provider Functions ==============

def call_gemini(messages: list, system_prompt: str) -> str:
    """Gemini 2.5 Flash - High quality for complex queries"""
    if not GEMINI_KEYS or not can_use_gemini():
        raise Exception("Gemini not available (no keys or quota exhausted)")
    
    print("🔷 Gemini 1.5 Flash...", end=" ", flush=True)
    
    # Try each key in rotation
    last_error = None
    for key in GEMINI_KEYS:
        try:
            client = genai.Client(api_key=key, http_options={'api_version': 'v1beta'})
            
            # Format messages for new SDK
            contents = [types.Content(role='user', parts=[types.Part(text=system_prompt)])]
            for m in messages:
                role = 'user' if m.get('role') == 'user' else 'model'
                contents.append(types.Content(role=role, parts=[types.Part(text=m.get('content', ''))]))
            
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(
                    temperature=0.7,
                    max_output_tokens=512,
                )
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
        except requests.exceptions.RequestException:
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
    # Try providers in order (Sequential Fallback for Sync Calls)
    # Note: chat() is the legacy sync entry point. Use chat_async() for speed.
    last_message = messages[-1].get("content", "") if messages else ""
    task_type = classify_task(last_message)
    providers = select_providers(task_type)
    
    # Offline fallback
    if offline_only:
        providers = [call_ollama]
    else:
        providers.append(call_ollama)

    last_error = None
    for fn in providers:
        try:
            return fn(messages, system_prompt)
        except Exception as e:
            last_error = e
            # error_msg = str(e)[:80]
            # print(f"✗ ({error_msg})")
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
