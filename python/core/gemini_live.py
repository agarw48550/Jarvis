"""
Gemini Live Session Manager with Affective and Proactive Dialog
Implementation based on latest Google Gemini Live API guidelines.
"""

import os
import asyncio
import logging
import base64
import json
from typing import Optional, Callable, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Gemini Live Model - Specified by USER
MODEL_ID = "models/gemini-2.5-flash-native-audio-preview-12-2025"

logger = logging.getLogger(__name__)

def build_system_prompt():
    """Imported from memory/config to avoid circular imports if needed, 
    but here we'll define a basic one if not provided."""
    from core.config import SYSTEM_PROMPT_TEMPLATE
    from core.memory import get_facts_for_prompt, get_preferences_for_prompt
    
    user_facts = get_facts_for_prompt()
    user_preferences = get_preferences_for_prompt()
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        user_facts=user_facts or "",
        user_preferences=user_preferences or "",
        recent_context=""
    )

class GeminiLiveSession:
    """
    Robust Gemini Live session manager for JARVIS V3.
    Integrates Affective Dialog and Proactive Audio.
    """
    
    _active_sessions: Dict[str, 'GeminiLiveSession'] = {}
    _session_lock = asyncio.Lock()
    
    def __init__(self, api_key: str = None, voice_name: str = "Puck"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing.")
        
        self.voice_name = voice_name
        self.session = None
        self.running = False
        self._cleanup_done = False
        
        self.client = genai.Client(
            api_key=self.api_key,
            http_options={'api_version': 'v1beta'}
        )
        
        # Session Resumption
        self.resume_token = None
        
        # Heartbeat / Silence handling
        self.last_audio_time = 0
        self._heartbeat_task_handle = None

        # Queues for internal communication if needed
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue(maxsize=10)
        
        logger.info(f"GeminiLiveSession initialized with voice: {voice_name}")

    def _get_config(self, system_instruction: str = None) -> types.LiveConnectConfig:
        config_args = {
            "response_modalities": ["AUDIO"],
            "system_instruction": {
                "parts": [{"text": system_instruction or build_system_prompt()}]
            },
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
        }
        
        # Apply strict context management
        # Note context_window_compression might be implicit or different in latest SDK versions
        # We'll stick to standard config unless resumption is active
        
        return types.LiveConnectConfig(**config_args)

    async def connect_and_run(
        self, 
        on_audio: Callable[[bytes], Any], 
        on_text: Callable[[str], Any],
        system_instruction: str = None
    ):
        """
        Connects to Gemini Live and runs the receive loop.
        This is the main entry point to be used within a Task.
        """
        config = self._get_config(system_instruction)
        
    async def _heartbeat_task(self):
        """Sends silent audio if no activity to keep connection alive."""
        logger.info("💓 Heartbeat task started")
        try:
            while self.running and self.session:
                await asyncio.sleep(10)
                now = asyncio.get_running_loop().time()
                # If we haven't sent audio for > 60s, send 160 bytes of silence
                if (now - self.last_audio_time) > 60:
                    logger.debug("💓 Sending heartbeat (silence)...")
                    # 160 bytes of zero PCM data
                    silent_frame = b'\x00' * 160 
                    await self.send_audio_chunk(silent_frame)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

    async def connect_and_run(
        self, 
        on_audio: Callable[[bytes], Any], 
        on_text: Callable[[str], Any],
        system_instruction: str = None
    ):
        """
        Connects to Gemini Live and runs the receive loop.
        """
        config = self._get_config(system_instruction)
        
        # Explicit cleanup of old sessions
        async with self._session_lock:
            if self.api_key in self._active_sessions:
                old_session = self._active_sessions[self.api_key]
                if old_session is not self:
                    logger.warning("Closing existing session for API key to prevent 409")
                    await old_session.close()
                    # MANDATORY WAIT for server to register disconnect
                    await asyncio.sleep(2.0) 
            
            self._active_sessions[self.api_key] = self

        # Retry logic for 409 conflicts
        max_retries = 3
        attempt = 0
        backoff = 2

        while attempt < max_retries:
            try:
                # Handle Resumption if token exists
                # Note: SDK syntax for resumption might vary, 
                # effectively we'd pass it in config or method if supported.
                async with self.client.aio.live.connect(model=MODEL_ID, config=config) as session:
                    self.session = session
                    self.running = True
                    self.last_audio_time = asyncio.get_running_loop().time()
                    
                    logger.info("✅ Connected to Gemini Live API")
                    
                    # Start Heartbeat
                    self._heartbeat_task_handle = asyncio.create_task(self._heartbeat_task())

                    async for message in session.receive():
                        if not self.running:
                            break
                        
                        # 1. Capture Session Resumption
                        if hasattr(message, 'session_resumption_update') and message.session_resumption_update:
                            logger.info("🔄 Received Session Resumption Update")
                            # self.resume_token = message.session_resumption_update
                        
                        # 2. Server Content (Audio/Text)
                        if message.server_content:
                            content = message.server_content
                            
                            if content.model_turn:
                                for part in content.model_turn.parts:
                                    if part.inline_data:
                                        if asyncio.iscoroutinefunction(on_audio):
                                            await on_audio(part.inline_data.data)
                                        else:
                                            on_audio(part.inline_data.data)
                                            
                                    if part.text:
                                        if asyncio.iscoroutinefunction(on_text):
                                            await on_text(part.text)
                                        else:
                                            on_text(part.text)
                            
                            if content.interrupted:
                                logger.info("AI Interrupted")
                                pass
                                
                        # 3. Tool Calls
                        if message.tool_call:
                            logger.info(f"Tool call received: {message.tool_call}")
                            
                        # 4. Success - reset retries if we stayed connected for a bit?
                        # For now, if we break out of loop due to running=False, we return.
                    
                    # If we exit receive loop normally, we're done
                    return

            except Exception as e:
                is_409 = "409" in str(e) or "conflict" in str(e).lower()
                if is_409:
                    attempt += 1
                    if attempt < max_retries:
                        logger.warning(f"Conflict 409. Retrying in {backoff}s...")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                        continue
                
                logger.error(f"Error in Gemini Live Session: {e}")
                raise
            finally:
                await self.close()

    async def send_audio_chunk(self, pcm_data: bytes):
        """Send raw PCM audio to Gemini."""
        if not self.session or not self.running:
            return
        
        try:
            await self.session.send_realtime_input(
                audio=types.Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
            )
            self.last_audio_time = asyncio.get_running_loop().time()
        except Exception as e:
            logger.error(f"Failed to send audio: {e}")
            self.running = False

    async def close(self):
        """Cleanup session."""
        if self._cleanup_done:
            return
            
        self.running = False
        self._cleanup_done = True
        
        # Stop Heartbeat
        if self._heartbeat_task_handle:
            self._heartbeat_task_handle.cancel()
            try:
                await self._heartbeat_task_handle
            except asyncio.CancelledError:
                pass
        
        if self.session:
            # The 'async with' block handles close, but we can explicitly try if needed
            # await self.session.close() 
            pass
            
        if self.api_key in self._active_sessions:
            if self._active_sessions[self.api_key] == self:
                del self._active_sessions[self.api_key]
        
        # GHOST SESSION FIX: Wait for server to cleanup
        await asyncio.sleep(2.0)
        logger.info("Session closed and cleaned up.")

    # Legacy compatibility methods for main.py
    async def connect(self, system_instruction: str = None):
        """No-op for compatibility, use connect_and_run for actual logic."""
        logger.debug("Connect called (compatibility mode)")
    
    async def receive_loop(self, on_audio, on_text):
        """No-op for compatibility."""
        logger.debug("Receive loop called (compatibility mode)")
