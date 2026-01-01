import asyncio
import os
import sys
import pyaudio
import time
import numpy as np
import traceback
import subprocess
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- 1. CLEAN START ---
# Force kill any hidden jarvis processes that might be holding a session open
try:
    subprocess.run(["pkill", "-9", "-f", "jarvis_live_cli.py"], capture_output=True)
except:
    pass

load_dotenv()
# Prioritize Key 2 and 1 to rotate away from potentially "locked" sessions
KEYS = [os.getenv("GEMINI_API_KEY_2"), os.getenv("GEMINI_API_KEY_1"), os.getenv("GEMINI_API_KEY")]
KEYS = [k for k in KEYS if k]

if not KEYS:
    print("❌ Critical: No API keys found in .env.")
    sys.exit(1)

# --- 2. CONFIGURATION ---
MODEL = "gemini-2.5-flash-native-audio-latest"
CHUNK_SIZE = 512
SEND_RATE = 16000
RECV_RATE = 24000
THRESHOLD = 0.005 # Sensitivity for hearing user

# --- 3. STATE ---
STATE = {
    "key_idx": 0,
    "handle": None,
    "active": True,
    "is_ai_active": False,
    "last_mic_sent_at": 0
}

class UltraAudio:
    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.in_stream = self.pya.open(format=pyaudio.paInt16, channels=1, rate=SEND_RATE, input=True, frames_per_buffer=CHUNK_SIZE)
        self.out_stream = self.pya.open(format=pyaudio.paInt16, channels=1, rate=RECV_RATE, output=True)
        self.playback_queue = asyncio.Queue()
        self.running = True

    async def playback_worker(self):
        """Dedicated thread for playing audio pieces."""
        loop = asyncio.get_event_loop()
        while self.running:
            try:
                data = await self.playback_queue.get()
                await loop.run_in_executor(None, self.out_stream.write, data)
            except:
                continue

    def get_rms(self, data):
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        return np.sqrt(np.mean(samples**2))

    def read_mic(self):
        return self.in_stream.read(CHUNK_SIZE, exception_on_overflow=False)

    def close(self):
        self.running = False
        try:
            self.in_stream.stop_stream()
            self.in_stream.close()
            self.out_stream.stop_stream()
            self.out_stream.close()
        except: pass
        self.pya.terminate()

async def start_session():
    audio = UltraAudio()
    worker_task = asyncio.create_task(audio.playback_worker())
    
    key = KEYS[STATE["key_idx"]]
    print(f"\n📡 [ENGINE] Connecting to {MODEL} using Key {STATE['key_idx'] + 1}...")
    
    client = genai.Client(api_key=key, http_options={'api_version': 'v1alpha'})
    
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        # Grounding Tools enabled for real-world utility
        tools=[types.Tool(google_search=types.GoogleSearch())],
        context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
        session_resumption=types.SessionResumptionConfig(handle=STATE["handle"]),
        system_instruction="You are Jarvis, a helpful and direct AI assistant. If you need info, use tools."
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ [ENGINE] Session Linked. Ready for multi-turn.")
            STATE["is_ai_active"] = False

            async def send_loop():
                """Clocks mic input and handles heartbeats."""
                chunk_duration = CHUNK_SIZE / SEND_RATE
                while True:
                    t_start = time.perf_counter()
                    data = await asyncio.get_event_loop().run_in_executor(None, audio.read_mic)
                    
                    if not STATE["is_ai_active"]:
                        rms = audio.get_rms(data)
                        # NOISE GATE + HEARTBEAT:
                        # If speaking, send data. If silent, send silence to keep socket hot.
                        to_send = data if rms > THRESHOLD else b'\x00' * (CHUNK_SIZE * 2)
                        await session.send_realtime_input(audio=types.Blob(data=to_send, mime_type="audio/pcm;rate=16000"))
                    else:
                        # Clears mic buffer while AI speaks
                        pass

                    elapsed = time.perf_counter() - t_start
                    await asyncio.sleep(max(0, chunk_duration - elapsed))

            async def receive_loop():
                """Handles all incoming messages from Gemini."""
                async for response in session.receive():
                    # Status Updates
                    if response.session_resumption_update:
                        STATE["handle"] = response.session_resumption_update.new_handle

                    if response.go_away:
                        print(f"⚠️ [ENGINE] Server GoAway signal. Time left: {response.go_away.time_left}")

                    # Content Logic
                    if response.server_content:
                        content = response.server_content
                        
                        if content.model_turn:
                            STATE["is_ai_active"] = True
                            for part in content.model_turn.parts:
                                if part.inline_data:
                                    audio.playback_queue.put_nowait(part.inline_data.data)

                        if content.turn_complete:
                            await asyncio.sleep(0.3) # Settlement time
                            STATE["is_ai_active"] = False

                        if content.interrupted:
                            STATE["is_ai_active"] = False
                            while not audio.playback_queue.empty(): audio.playback_queue.get_nowait()
                            print("🚨 [ENGINE] Interruption Detected.")

                        if content.input_transcription:
                            print(f"👤 You: {content.input_transcription.text}")
                        if content.output_transcription:
                            print(f"🤖 Jarvis: {content.output_transcription.text}")

                    # Tool Visibility
                    if response.tool_call:
                        print("🛠️ [ENGINE] Fetching live data...")

            await asyncio.gather(send_loop(), receive_loop())

    except Exception as e:
        err_msg = str(e)
        if "409" in err_msg or "403" in err_msg:
            print(f"🛑 [ENGINE] Conflict/Limit on Key {STATE['key_idx']+1}. Pivoting...")
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            return True # Retry signal
        else:
            print(f"❌ [ENGINE] Core Error: {e}")
            return False
    finally:
        worker_task.cancel()
        audio.close()
    return False

async def main():
    while STATE["active"]:
        restart_needed = await start_session()
        if not restart_needed:
            if STATE["active"]:
                print("🔄 [ENGINE] Restarting session in 3s...")
                await asyncio.sleep(3)
        else:
            await asyncio.sleep(0.5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        STATE["active"] = False
        print("\n👋 [ENGINE] Offline. Goodbye.")
