#!/usr/bin/env python3
"""
Backwards compatibility wrapper for llm_router
Redirects to new modular LLM router
"""

from core.llm_router import chat, check_api_keys, detect_complexity

# Backwards compatibility
__all__ = ['chat', 'check_api_keys', 'detect_complexity']
