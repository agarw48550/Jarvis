#!/usr/bin/env python3
"""
Dual-Brain Orchestrator
Handles connectivity detection, mode switching, and resource monitoring
"""

import requests
import socket
from typing import Literal, Optional
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.llm_router import chat, check_api_keys


Mode = Literal["online", "offline"]


class JarvisOrchestrator:
    """Main orchestrator for JARVIS brain"""
    
    def __init__(self):
        self.mode: Mode = "online"
        self.force_mode: Optional[Mode] = None  # User-forced mode
        
    def check_connectivity(self) -> bool:
        """
        Check if online connectivity is available.
        Tries multiple methods for reliability.
        """
        # Try 1: DNS check (Google DNS)
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            return True
        except OSError:
            pass
        
        # Try 2: HTTP request to Google
        try:
            response = requests.get("https://www.google.com", timeout=3)
            return response.status_code == 200
        except:
            pass
        
        # Try 3: DNS resolution
        try:
            socket.gethostbyname("google.com")
            return True
        except:
            pass
        
        return False
    
    def detect_mode(self) -> Mode:
        """Detect current mode based on connectivity and user preference"""
        # User-forced mode takes precedence
        if self.force_mode:
            return self.force_mode
        
        # Auto-detect based on connectivity
        if self.check_connectivity():
            return "online"
        else:
            return "offline"
    
    def switch_mode(self, mode: Mode):
        """Switch to specified mode (online/offline)"""
        self.force_mode = mode
        self.mode = mode
        print(f"🔄 Mode switched to: {mode}")
    
    def enable_private_mode(self):
        """Enable private mode (offline/local only)"""
        self.switch_mode("offline")
    
    def disable_private_mode(self):
        """Disable private mode (auto-detect)"""
        self.force_mode = None
        self.mode = self.detect_mode()
        print(f"🔄 Mode set to auto-detect: {self.mode}")
    
    def get_llm_response(self, messages: list, system_prompt: str) -> str:
        """
        Get LLM response, routing based on current mode.
        The router already handles online/offline fallbacks.
        """
        # Update mode detection
        if not self.force_mode:
            self.mode = self.detect_mode()
        
        # The chat() function in llm_router handles fallbacks
        try:
            return chat(messages, system_prompt, offline_only=(self.mode == "offline"))
        except Exception as e:
            # If online fails and we're not forcing offline, try offline explicitly
            if self.mode == "online":
                print("⚠️ Online mode failed, trying offline fallback...")
                try:
                    from core.llm_router import call_ollama
                    return call_ollama(messages, system_prompt)
                except:
                    pass
            raise e
    
    def get_status(self) -> dict:
        """Get orchestrator status"""
        return {
            "mode": self.mode,
            "forced": self.force_mode is not None,
            "online": self.check_connectivity(),
        }
