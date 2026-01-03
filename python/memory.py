#!/usr/bin/env python3
"""
Backwards compatibility wrapper for memory
Redirects to new modular memory system
"""

from core.memory import (
    add_fact, get_all_facts, get_facts_for_prompt,
    clear_memory, load_memory, save_memory,
    add_message, get_relevant_context, search_facts,
    init_database
)

# Backwards compatibility
__all__ = [
    'add_fact', 'get_all_facts', 'get_facts_for_prompt',
    'clear_memory', 'load_memory', 'save_memory',
    'add_message', 'get_relevant_context', 'search_facts',
    'init_database'
]
