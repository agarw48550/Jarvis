#!/usr/bin/env python3
"""
Simple JSON-based memory for storing user facts
"""

import json
import os
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path(__file__).parent / "jarvis_memory.json"

def load_memory() -> dict:
    """Load memory from JSON file"""
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {"facts": [], "conversation_count": 0}
    return {"facts": [], "conversation_count": 0}

def save_memory(memory: dict):
    """Save memory to JSON file"""
    with open(MEMORY_FILE, 'w') as f:
        json.dump(memory, f, indent=2, default=str)

def add_fact(fact: str, category: str = "general"):
    """Add a fact to memory"""
    memory = load_memory()
    
    # Check if fact already exists
    for existing in memory["facts"]:
        if existing["fact"].lower() == fact.lower():
            return False  # Already exists
    
    memory["facts"].append({
        "fact": fact,
        "category": category,
        "added_at": datetime.now().isoformat()
    })
    save_memory(memory)
    print(f"💾 Saved to memory: {fact}")
    return True

def get_all_facts() -> list:
    """Get all stored facts"""
    memory = load_memory()
    return memory.get("facts", [])

def get_facts_for_prompt() -> str:
    """Get facts formatted for system prompt"""
    facts = get_all_facts()
    if not facts:
        return "I don't have any saved information about the user yet."
    
    return "Things I know about the user:\n" + "\n".join(
        f"- {f['fact']}" for f in facts
    )

def clear_memory():
    """Clear all memory"""
    save_memory({"facts": [], "conversation_count": 0})
    print("🗑️ Memory cleared")

def increment_conversation_count():
    """Track number of conversations"""
    memory = load_memory()
    memory["conversation_count"] = memory.get("conversation_count", 0) + 1
    save_memory(memory)
    return memory["conversation_count"]
