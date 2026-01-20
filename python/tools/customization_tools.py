#!/usr/bin/env python3
"""
Tools for users to customize the AI's personality and behavior.
"""

from core.memory import set_preference, get_preference

def update_ai_behavior(style_key: str, value: str) -> str:
    """
    Update a specific aspect of the AI's behavior or personality.
    Allowed keys: voice_style, humor_level, conversation_style, formality, response_length
    """
    allowed_keys = [
        "voice_style", "humor_level", "conversation_style", 
        "formality", "response_length"
    ]
    
    key = style_key.lower().replace(" ", "_").strip()
    
    # Fuzzy matching for keys
    if "humor" in key: key = "humor_level"
    elif "formal" in key: key = "formality"
    elif "length" in key or "short" in key or "long" in key: key = "response_length"
    elif "voice" in key: key = "voice_style"
    elif "style" in key: key = "conversation_style"
    
    if key not in allowed_keys:
        return f"Unknown style setting '{style_key}'. Use one of: {', '.join(allowed_keys)}"
        
    set_preference(key, value)
    
    return f"Okay, I've updated my {key.replace('_', ' ')} to be: {value}. I'll adapt immediately."
