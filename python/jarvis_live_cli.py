import asyncio
import os
import sys
import pyaudio
import time
import numpy as np
import signal
import atexit
import uuid
from google import genai
from google.genai import types
from core.config import API_KEYS, MODELS, AUDIO, SYSTEM_PROMPT

# --- GLOBAL STATE ---
KEYS = API_KEYS.gemini_keys
if not KEYS:
    print("❌ Critical: No API keys found in .env.")
    sys.exit(1)

MODEL = MODELS.gemini_live_model
CHUNK_SIZE = AUDIO.chunk_size
SEND_RATE = AUDIO.input_sample_rate
RECV_RATE = AUDIO.output_sample_rate
THRESHOLD = AUDIO.voice_threshold

STATE = {
    "key_idx": 0,
    "active": True,
    "is_ai_active": False,
    "key_cooldowns": {}
}

# Conversation memory
CONVERSATION_HISTORY = []
MAX_HISTORY = 10  # Keep last 10 exchanges

_cleanup_done = False

# --- CLEANUP HANDLERS ---
def cleanup():
    """Cleanup function called on exit"""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    print("\n🧹 [SYSTEM] Cleaning up resources...")
    STATE["active"] = False

atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: cleanup())
signal.signal(signal.SIGTERM, lambda s, f: cleanup())

# --- AUDIO HANDLER ---
class UltraAudio:
    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.in_stream = self.pya.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=SEND_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )
        self.out_stream = self.pya.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RECV_RATE,
            output=True
        )
        self.playback_queue = asyncio.Queue()
        self.running = True

    async def playback_worker(self):
        """Dedicated worker for playing audio"""
        loop = asyncio.get_event_loop()
        while self.running and STATE["active"]:
            try:
                data = await asyncio.wait_for(self.playback_queue.get(), timeout=0.1)
                await loop.run_in_executor(None, self.out_stream.write, data)
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    print(f"Playback error: {e}")
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
        except:
            pass
        self.pya.terminate()

# --- CONVERSATION MEMORY ---
def get_system_prompt_with_context():
    """Build system prompt with conversation history"""
    base_prompt = SYSTEM_PROMPT
    
    if CONVERSATION_HISTORY:
        history_text = "\n\nRecent conversation context:\n"
        for msg in CONVERSATION_HISTORY[-6:]:  # Last 3 exchanges
            role = "User" if msg["role"] == "user" else "Jarvis"
            history_text += f"{role}: {msg['text']}\n"
        return base_prompt + history_text
    
    return base_prompt

# --- SESSION LOGIC ---
async def start_session():
    session_id = str(uuid.uuid4())[:8]
    audio = UltraAudio()
    worker_task = None
    send_task = None
    receive_task = None
    
    # Key rotation with cooldown
    now = time.time()
    for _ in range(len(KEYS)):
        current_k_idx = STATE["key_idx"]
        last_error = STATE["key_cooldowns"].get(current_k_idx, 0)
        
        if now - last_error < 60:
            print(f"⚠️ [ENGINE] Key {current_k_idx+1} on cooldown. Skipping.")
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            continue
        break
    
    key = KEYS[STATE["key_idx"]]
    print(f"\n📡 [ENGINE] Session {session_id}: Connecting to {MODEL} using Key {STATE['key_idx'] + 1}...")
    
    client = genai.Client(
        api_key=key,
        http_options={'api_version': MODELS.gemini_live_api_version}
    )
    
    # NO session resumption - fresh session each time with context from memory
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        tools=[types.Tool(google_search=types.GoogleSearch())],
        system_instruction=get_system_prompt_with_context()
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print(f"✅ [ENGINE] Session {session_id}: Linked.")
            print("🎧 [ENGINE] Listening...")
            STATE["is_ai_active"] = False
            
            worker_task = asyncio.create_task(audio.playback_worker())
            
            async def send_loop():
                """Streams mic audio to Gemini, pausing during AI speech"""
                chunk_duration = CHUNK_SIZE / SEND_RATE
                chunks_sent = 0
                last_log = time.time()
                
                while STATE["active"]:
                    t_start = time.perf_counter()
                    
                    # Always read mic to prevent buffer overflow
                    data = await asyncio.get_event_loop().run_in_executor(None, audio.read_mic)
                    
                    # Only send audio when AI is NOT speaking (prevents false interruptions)
                    if not STATE["is_ai_active"]:
                        try:
                            await session.send_realtime_input(
                                audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                            )
                            chunks_sent += 1
                        except Exception as e:
                            if STATE["active"]:
                                print(f"⚠️ [ENGINE] Send error: {e}")
                            break
                    else:
                        # AI is speaking - only send if user is LOUDLY interrupting
                        rms = audio.get_rms(data)
                        if rms > THRESHOLD * 3:  # Much higher threshold for intentional interruption
                            print("🎤 [ENGINE] User interrupting...")
                            try:
                                await session.send_realtime_input(
                                    audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                                )
                            except:
                                pass
                    
                    # Debug logging every 5 seconds
                    if time.time() - last_log > 5:
                        rms = audio.get_rms(data)
                        status = "🔇 Paused (AI speaking)" if STATE["is_ai_active"] else "🎙️ Streaming"
                        print(f"📊 [DEBUG] {status} | Sent: {chunks_sent} | RMS: {rms:.4f}")
                        chunks_sent = 0
                        last_log = time.time()
                    
                    elapsed = time.perf_counter() - t_start
                    await asyncio.sleep(max(0, chunk_duration - elapsed))

            async def receive_loop():
                """Handles all incoming messages from Gemini"""
                try:
                    async for response in session.receive():
                        if not STATE["active"]:
                            break
                            
                        # Content Logic
                        if response.server_content:
                            content = response.server_content
                            
                            if content.model_turn:
                                STATE["is_ai_active"] = True
                                for part in content.model_turn.parts:
                                    if part.inline_data:
                                        audio.playback_queue.put_nowait(part.inline_data.data)
                                    if part.text:
                                        print(f"🤖 Jarvis: {part.text}")

                            if content.turn_complete:
                                STATE["is_ai_active"] = False
                                await asyncio.sleep(0.5)  # Wait 500ms before accepting new input
                                print("🎧 [ENGINE] Listening...")

                            if content.interrupted:
                                STATE["is_ai_active"] = False
                                # Clear playback queue
                                while not audio.playback_queue.empty():
                                    try:
                                        audio.playback_queue.get_nowait()
                                    except:
                                        break
                                print("🚨 [ENGINE] Interrupted - Listening...")
                                # DON'T break or end session - just continue listening!

                            # Transcriptions - save to history
                            if hasattr(content, 'input_transcription') and content.input_transcription:
                                if content.input_transcription.text:
                                    text = content.input_transcription.text.strip()
                                    if text:
                                        CONVERSATION_HISTORY.append({"role": "user", "text": text})
                                        print(f"👤 You: {text}")
                                        
                            if hasattr(content, 'output_transcription') and content.output_transcription:
                                if content.output_transcription.text:
                                    text = content.output_transcription.text.strip()
                                    if text:
                                        CONVERSATION_HISTORY.append({"role": "assistant", "text": text})
                                        # Don't print here - already printed from inline_data
                            
                            # Trim history to last N exchanges
                            if len(CONVERSATION_HISTORY) > MAX_HISTORY * 2:
                                CONVERSATION_HISTORY[:] = CONVERSATION_HISTORY[-MAX_HISTORY * 2:]

                        # Tool calls
                        if response.tool_call:
                            print("🛠️ [ENGINE] Using tool...")
                            
                        # Go away signal
                        if response.go_away:
                            print(f"⚠️ [ENGINE] Server ending session soon...")
                            
                except Exception as e:
                    if STATE["active"]:
                        print(f"❌ [ENGINE] Receive error: {e}")

            send_task = asyncio.create_task(send_loop())
            receive_task = asyncio.create_task(receive_loop())
            
            # Wait for either to complete (or error)
            done, pending = await asyncio.wait(
                [send_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        err_msg = str(e)
        if "409" in err_msg:
            print(f"🛑 [ENGINE] Session conflict. Rotating key...")
            STATE["key_cooldowns"][STATE["key_idx"]] = time.time()
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            return True
        elif "1008" in err_msg:
            print(f"❌ [ENGINE] Invalid model or config: {err_msg[:100]}")
            return False
        else:
            print(f"❌ [ENGINE] Error: {err_msg[:100]}")
            return False
    finally:
        if worker_task:
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        if send_task and not send_task.done():
            send_task.cancel()
        if receive_task and not receive_task.done():
            receive_task.cancel()
        audio.close()
        
    return False

async def main():
    print("🤖 JARVIS Voice Assistant Starting...")
    print(f"📍 Model: {MODEL}")
    print("💡 Tip: Speak naturally. Press Ctrl+C to exit.\n")
    
    retry_count = 0
    max_retries = 3
    
    while STATE["active"]:
        try:
            restart_needed = await start_session()
            
            if restart_needed:
                retry_count += 1
                if retry_count >= max_retries:
                    print("❌ [ENGINE] Max retries reached. Exiting...")
                    break
                await asyncio.sleep(1)
            else:
                retry_count = 0
                if STATE["active"]:
                    print("🔄 [ENGINE] Session ended. Reconnecting in 2s...")
                    await asyncio.sleep(2)
                    
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"❌ [ENGINE] Unexpected error: {e}")
            await asyncio.sleep(2)
    
    print("👋 [ENGINE] Goodbye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # cleanup() handles this via atexit
