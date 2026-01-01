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
        self.api_key = api_key or os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY_2") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing. Please set it in .env file.")
        self.voice_name = voice_name
        self.client = genai.Client(api_key=self.api_key, http_options={'api_version': 'v1beta'})
        self.session_ctx = None
        self.running = False
        self.logger = logging.getLogger("GeminiLive")
        self.logger.setLevel(logging.INFO)

    async def connect(self, system_instruction: str = None):
        """Build the connect configuration"""
        self.connect_config = LiveConnectConfig(
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
        self.running = True
        self.logger.info(f"✅ Gemini Live Client Initialized (Model: {MODEL_ID})")

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
        if not self.running:
            return

        try:
            async with self.client.aio.live.connect(model=MODEL_ID, config=self.connect_config) as session:
                self.session_ctx = session
                self.logger.info("📡 WebSocket Session Active")
                async for message in session.receive():
                    if message.server_content:
                        content = message.server_content
                        if content.model_turn:
                            for part in content.model_turn.parts:
                                if part.inline_data and on_audio:
                                    on_audio(part.inline_data.data)
                                if part.text and on_text:
                                    on_text(part.text)
                        
                        if content.turn_complete:
                            self.logger.info("🏁 Turn complete")
                        
                        if content.interrupted:
                            self.logger.info("🚨 AI Interrupted")

                    if message.tool_call:
                        self.logger.info(f"🔧 Tool call: {message.tool_call}")

        except Exception as e:
            if self.running:
                self.logger.error(f"Session error: {e}")
            self.running = False
        finally:
            self.session_ctx = None

    async def close(self):
        self.running = False
        self.session_ctx = None
        self.logger.info("🔌 Gemini Session Requested Close")
