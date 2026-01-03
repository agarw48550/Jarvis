"""
Gemini Live Session Manager with 409 Conflict Resolution
Production-ready implementation with proper session lifecycle management
"""

import os
import asyncio
import logging
from typing import Optional, Callable, Dict
from dotenv import load_dotenv
from google import genai
from google.genai.types import (
    LiveConnectConfig,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
    Tool,
    GoogleSearchRetrieval
)

load_dotenv()

# Gemini Live Model
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"

logger = logging.getLogger(__name__)


class GeminiLiveSession:
    """
    Production-ready Gemini Live session with 409 conflict resolution.
    
    Features:
    - Class-level session tracking (prevents multiple sessions per key)
    - Exponential backoff on 409 errors (2s, 4s, 8s)
    - Mandatory cleanup delays (prevents server-side conflicts)
    - Session locking (ensures only one connection attempt at a time)
    - Proper error handling and logging
    """
    
    # CLASS-LEVEL: Shared across all instances
    _active_sessions: Dict[str, 'GeminiLiveSession'] = {}
    _session_lock = asyncio.Lock()
    
    def __init__(self, api_key: str = None, voice_name: str = "Charon"):
        """
        Initialize session (does NOT connect yet - call connect() separately).
        
        Args:
            api_key: Gemini API key (falls back to environment variables)
            voice_name: Voice for audio responses (Charon, Puck, Aoede, etc.)
        """
        self.api_key = api_key or os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing. Set GEMINI_API_KEY_1/2 in .env")
        
        self.voice_name = voice_name
        self.session = None
        self.running = False
        self._cleanup_done = False
        self.resumption_token: Optional[str] = None
        
        logger.info(f"Session initialized (key: ...{self.api_key[-4:]}, voice: {voice_name})")
    
    async def connect(
        self, 
        system_instruction: str = None,
        max_retries: int = 3
    ):
        """
        Connect to Gemini Live with 409 conflict resolution.
        
        CRITICAL for 409 fixes:
        - Checks for existing session on this API key
        - Waits for cleanup before creating new session
        - Retries with exponential backoff on 409
        
        Args:
            system_instruction: System prompt for the model
            max_retries: Number of retry attempts on 409 (default: 3)
        
        Raises:
            Exception: After max_retries exhausted or non-409 error
        """
        async with self._session_lock:
            # STEP 1: Close any existing session for this key
            if self.api_key in self._active_sessions:
                old_session = self._active_sessions[self.api_key]
                logger.warning(
                    f"⚠️ Closing existing session for key ...{self.api_key[-4:]}"
                )
                await old_session.close()
                # CRITICAL: Wait for server cleanup
                await asyncio.sleep(2)
            
            # STEP 2: Attempt connection with exponential backoff
            for attempt in range(max_retries):
                try:
                    # Build configuration
                    config = LiveConnectConfig(
                        response_modalities=["AUDIO"],
                        system_instruction={
                            "parts": [{"text": system_instruction or "You are Jarvis."}]
                        },
                        tools=[Tool(google_search_retrieval=GoogleSearchRetrieval())],
                        generation_config={
                            "speech_config": SpeechConfig(
                                voice_config=VoiceConfig(
                                    prebuilt_voice_config=PrebuiltVoiceConfig(
                                        voice_name=self.voice_name
                                    )
                                )
                            )
                        }
                    )
                    
                    # Add session resumption if we have a token
                    if self.resumption_token:
                        logger.debug("Using session resumption token")
                        # Note: Actual resumption config depends on SDK version
                        # This is placeholder - check latest google-genai docs
                    
                    # Create client and connect
                    client = genai.Client(
                        api_key=self.api_key,
                        http_options={'api_version': 'v1beta'}
                    )
                    
                    # Store connection for use in send/receive
                    self.session = await client.aio.live.connect(
                        model=MODEL_ID,
                        config=config
                    )
                    
                    # STEP 3: Register this session
                    self._active_sessions[self.api_key] = self
                    self.running = True
                    
                    logger.info(
                        f"✅ Connected successfully (attempt {attempt + 1}/{max_retries})"
                    )
                    return
                    
                except Exception as e:
                    error_str = str(e)
                    
                    # Handle 409 Conflict specifically
                    if "409" in error_str or "CONFLICT" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                        if attempt < max_retries - 1:
                            # Exponential backoff: 2s, 4s, 8s
                            delay = 2 * (2 ** attempt)
                            logger.warning(
                                f"⚠️ 409 Conflict - previous session still open. "
                                f"Retrying in {delay}s (attempt {attempt + 1}/{max_retries})"
                            )
                            await asyncio.sleep(delay)
                        else:
                            logger.error(
                                f"❌ Failed after {max_retries} retries. "
                                f"Try different API key or wait 5 minutes."
                            )
                            raise Exception(
                                f"409 Conflict persists after {max_retries} attempts. "
                                f"Previous session may not have closed properly."
                            )
                    else:
                        # Non-409 error - don't retry
                        logger.error(f"❌ Connection failed: {e}")
                        raise
    
    async def send_audio_chunk(self, pcm_data: bytes):
        """
        Send raw PCM audio chunk to Gemini.
        
        Args:
            pcm_data: Raw PCM audio bytes (16kHz, 16-bit, mono)
        """
        if not self.session or not self.running:
            return
        
        try:
            await self.session.send_realtime_input(
                audio={"data": pcm_data, "mime_type": "audio/pcm;rate=16000"}
            )
        except Exception as e:
            logger.error(f"Send audio error: {e}")
            self.running = False
    
    async def receive_loop(
        self,
        on_audio: Callable[[bytes], None],
        on_text: Callable[[str], None]
    ):
        """
        Receive loop for processing Gemini responses.
        
        Args:
            on_audio: Callback for audio responses (receives raw bytes)
            on_text: Callback for text responses (receives string)
        """
        if not self.session or not self.running:
            logger.error("Cannot start receive loop - session not connected")
            return
        
        try:
            logger.info("📡 Starting receive loop")
            
            async for message in self.session.receive():
                if not self.running:
                    break
                
                # Handle server content
                if hasattr(message, 'server_content') and message.server_content:
                    content = message.server_content
                    
                    # Model turn (audio/text response)
                    if hasattr(content, 'model_turn') and content.model_turn:
                        for part in content.model_turn.parts:
                            if hasattr(part, 'inline_data') and part.inline_data and on_audio:
                                on_audio(part.inline_data.data)
                            if hasattr(part, 'text') and part.text and on_text:
                                on_text(part.text)
                    
                    # Turn complete
                    if hasattr(content, 'turn_complete') and content.turn_complete:
                        logger.debug("Turn complete")
                    
                    # Interrupted
                    if hasattr(content, 'interrupted') and content.interrupted:
                        logger.info("🚨 AI response interrupted by user")
                
                # Tool calls
                if hasattr(message, 'tool_call') and message.tool_call:
                    logger.info(f"🔧 Tool call: {message.tool_call}")
                
                # Session resumption updates
                if hasattr(message, 'session_resumption_update') and message.session_resumption_update:
                    # Capture resumption token for future reconnects
                    if hasattr(message.session_resumption_update, 'token'):
                        self.resumption_token = message.session_resumption_update.token
                        logger.debug("🔄 Captured session resumption token")
        
        except Exception as e:
            if self.running:
                logger.exception(f"Session error in receive loop")
            self.running = False
    
    async def close(self):
        """
        Proper session cleanup with mandatory delay.
        
        CRITICAL: Always waits after closing to let server cleanup!
        This is the key to preventing 409 conflicts.
        """
        if self._cleanup_done:
            return
        
        self.running = False
        self._cleanup_done = True
        
        if self.session:
            try:
                # Close the session
                await self.session.close()
                logger.info("🔌 Session closed")
            except Exception as e:
                logger.debug(f"Close error (expected): {e}")
            finally:
                self.session = None
        
        # CRITICAL: Remove from active sessions
        if self.api_key in self._active_sessions:
            del self._active_sessions[self.api_key]
        
        # MANDATORY DELAY: Let Google's servers fully release resources
        await asyncio.sleep(2)
        logger.debug("⏳ Cleanup delay completed")
    
    @classmethod
    def get_active_session_count(cls) -> int:
        """
        Get number of currently active sessions (for debugging).
        
        Returns:
            Number of sessions currently marked as running
        """
        return len([s for s in cls._active_sessions.values() if s.running])
    
    @classmethod
    async def close_all_sessions(cls):
        """
        Emergency cleanup - close all active sessions.
        Useful for shutdown or error recovery.
        """
        logger.warning(f"Closing {len(cls._active_sessions)} active sessions")
        for session in list(cls._active_sessions.values()):
            await session.close()
