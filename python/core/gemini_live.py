import os
import asyncio
import base64
import logging
from typing import Optional, Callable
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

# Exclusive Gemini 2.5 Native Audio Dialog Model
MODEL_ID = "gemini-2.5-flash-native-audio-preview-12-2025"

class GeminiLiveSession:
    def __init__(self, api_key: str = None, voice_name: str = "Charon"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2")
        self.voice_name = voice_name
        self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})
        self.session = None
        self.session_ctx = None
        self.running = False
        self.logger = logging.getLogger("GeminiLive")
        self.logger.setLevel(logging.INFO)

    async def connect(self, system_instruction: str = None):
        """Establish connection to Gemini Live using SDK"""
        try:
            # Native Audio models often require AUDIO modality explicitly
            config = LiveConnectConfig(
                response_modalities=["AUDIO"],
                system_instruction={"parts": [{"text": system_instruction or "You are Jarvis."}]},
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
            
            # Start session
            self.session = self.client.aio.live.connect(model=MODEL_ID, config=config)
            # We don't "await" the context manager here if we want to manage it manually,
            # but usually it's used as an async context manager.
            # To stick to the current class structure, we'll enter the context.
            self.session_ctx = await self.session.__aenter__()
            self.running = True
            self.logger.info(f"✅ Gemini Live Connected (Model: {MODEL_ID})")
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            self.running = False
            raise e

    async def send_audio_chunk(self, pcm_data: bytes):
        """Send raw PCM audio chunk"""
        if not self.session_ctx or not self.running:
            return

        try:
            # Use specific realtime input method for audio with Blob format
            await self.session_ctx.send_realtime_input(
                audio={"data": pcm_data, "mime_type": "audio/pcm;rate=16000"}
            )
        except Exception as e:
            self.logger.error(f"Send audio error: {e}")
            self.running = False

    async def receive_loop(self, on_audio: Callable[[bytes], None], on_text: Callable[[str], None]):
        """Listen for messages from Gemini"""
        try:
            async for message in self.session_ctx.receive():
                # self.logger.info(f"DEBUG: Message received") 
                
                if getattr(message.server_content, 'model_turn', None):
                    parts = message.server_content.model_turn.parts
                    for part in parts:
                        if part.inline_data:
                            if on_audio:
                                on_audio(part.inline_data.data)
                        if part.text:
                            if on_text:
                                on_text(part.text)
                
                # Handle Tool Calls (Search grounding handles internally or via tool_call)
                tool_call = getattr(message.server_content, 'tool_call', None)
                if tool_call:
                    self.logger.info(f"🔧 Tool call: {tool_call}")

                if getattr(message.server_content, 'turn_complete', None):
                    self.logger.info("🏁 Turn complete")

        except Exception as e:
            if self.running: # Don't log if we closed intentionally
                self.logger.error(f"Receive loop error: {e}")
            self.running = False

    async def close(self):
        self.running = False
        if self.session_ctx:
            await self.session.__aexit__(None, None, None)
        self.logger.info("🔌 Gemini Session Closed")
