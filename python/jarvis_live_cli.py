import asyncio
import sys
import pyaudio
import time
import numpy as np
import signal
import atexit
import uuid
from google import genai
from google.genai import types
from core.config import API_KEYS, MODELS, AUDIO, SYSTEM_PROMPT_TEMPLATE, VOICE_MAPPINGS
from core.memory import (
    init_database, 
    get_facts_for_prompt, 
    get_preferences_for_prompt,
    get_preference,
    set_preference
)

# Initialize database
try:
    init_database()
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}")

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
    "key_cooldowns": {},
    "session_handle": None,  # For session resumption
    "voice": None,  # Current voice setting
    "needs_voice_change": False,  # Signal to reconnect with new voice
    "cooldown_until": 0,  # Timestamp when we can resume sending audio
}

_cleanup_done = False

# --- TOOL DEFINITIONS ---
JARVIS_TOOLS = [
    types.FunctionDeclaration(
        name="exit_jarvis",
        description="Exit and close Jarvis when user says goodbye, exit, quit, or stop",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={}
        )
    ),
    types.FunctionDeclaration(
        name="change_voice",
        description="Change Jarvis voice. Options: Puck (default/neutral), Charon (deep male), Fenrir (bold male), Aoede (melodic female), Kore (warm female)",
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "voice_name": types.Schema(
                    type=types.Type.STRING,
                    description="The voice to use",
                    enum=["Puck", "Charon", "Fenrir", "Aoede", "Kore"]
                )
            },
            required=["voice_name"]
        )
    ),
]

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
signal.signal(signal.SIGINT, lambda _s, _f: (cleanup(), sys.exit(0)))
signal.signal(signal.SIGTERM, lambda _s, _f: (cleanup(), sys.exit(0)))

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
        consecutive_errors = 0
        while self.running and STATE["active"]:
            try:
                data = await asyncio.wait_for(self.playback_queue.get(), timeout=0.1)
                await loop.run_in_executor(None, self.out_stream.write, data)
                consecutive_errors = 0
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.running:
                    consecutive_errors += 1
                    print(f"Playback error: {e}")
                    if consecutive_errors >= 5:
                        print("Too many consecutive errors, stopping playback")
                        break
                    await asyncio.sleep(0.1)
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

# --- VOICE MANAGEMENT ---
def get_current_voice():
    """Get the current voice preference"""
    return STATE.get("voice") or get_preference("voice") or AUDIO.default_voice

# --- TOOL EXECUTION ---
def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return result string"""
    
    if name == "exit_jarvis":
        STATE["active"] = False
        return "Goodbye! Jarvis is shutting down."
    
    elif name == "change_voice":
        new_voice = args.get("voice_name", "Puck")
        STATE["voice"] = new_voice
        
        # Save to persistent memory
        set_preference("voice", new_voice)
        
        # Signal reconnection needed
        STATE["needs_voice_change"] = True
        
        return f"Switching to {new_voice} voice. One moment..."
    
    return f"Unknown tool: {name}"

# --- CONVERSATION MEMORY ---
def build_system_prompt():
    """Build system prompt with user facts and preferences"""
    user_facts = get_facts_for_prompt()
    user_preferences = get_preferences_for_prompt()
    
    # Build context
    context_parts = []
    if user_facts:
        context_parts.append(user_facts)
    if user_preferences:
        context_parts.append(user_preferences)
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        user_facts=user_facts if user_facts else "",
        user_preferences=user_preferences if user_preferences else "",
        recent_context=""  # Session resumption handles this
    )

# --- SESSION LOGIC ---
async def start_session():
    session_id = str(uuid.uuid4())[:8]
    audio = UltraAudio()
    worker_task = None
    send_task = None
    receive_task = None
    
    # Key rotation with cooldown
    now = time.time()
    all_on_cooldown = True
    for _ in range(len(KEYS)):
        current_k_idx = STATE["key_idx"]
        last_error = STATE["key_cooldowns"].get(current_k_idx, 0)
        
        if now - last_error < 60:
            print(f"⚠️ [ENGINE] Key {current_k_idx+1} on cooldown. Skipping.")
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            continue
        all_on_cooldown = False
        break
    
    if all_on_cooldown:
        print("⚠️ All keys on cooldown. Waiting 10 seconds...")
        await asyncio.sleep(10)
        STATE["key_cooldowns"].clear()
    
    key = KEYS[STATE["key_idx"]]
    current_voice = get_current_voice()
    
    # Show connection info
    if STATE.get("session_handle"):
        print(f"\n📡 [ENGINE] Session {session_id}: Resuming with voice '{current_voice}'...")
    else:
        print(f"\n📡 [ENGINE] Session {session_id}: New session with voice '{current_voice}'...")
    
    client = genai.Client(
        api_key=key,
        http_options={'api_version': MODELS.gemini_live_api_version}
    )
    
    # Configure voice
    speech_config = types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name=current_voice
            )
        )
    )
    
    # Build config with session resumption and context compression
    config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        speech_config=speech_config,
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
        
        # Session resumption - maintains context across reconnects
        session_resumption=types.SessionResumptionConfig(
            handle=STATE.get("session_handle")
        ),
        
        # Context window compression - allows infinite conversations
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(
                target_tokens=16000  # Keep ~16k tokens of context
            )
        ),
        
        # Tools
        tools=[
            types.Tool(google_search=types.GoogleSearch()),  # Built-in search
            types.Tool(function_declarations=JARVIS_TOOLS),  # Custom functions
        ],
        
        system_instruction=build_system_prompt()
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print(f"✅ [ENGINE] Session {session_id}: Linked.")
            print("🎧 [ENGINE] Listening...")
            STATE["is_ai_active"] = False
            
            worker_task = asyncio.create_task(audio.playback_worker())
            
            async def send_loop():
                """Streams audio to Gemini with echo prevention"""
                chunk_duration = CHUNK_SIZE / SEND_RATE
                chunks_sent = 0
                last_log = time.time()
                
                while STATE["active"]:
                    t_start = time.perf_counter()
                    
                    # Always read mic to clear buffer (prevents overflow)
                    data = await asyncio.get_event_loop().run_in_executor(None, audio.read_mic)
                    
                    current_time = time.time()
                    
                    # Check if we should send audio
                    should_send = (
                        not STATE["is_ai_active"] and  # AI not speaking
                        current_time > STATE["cooldown_until"]  # Past cooldown period
                    )
                    
                    if should_send:
                        try:
                            await session.send_realtime_input(
                                audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                            )
                            chunks_sent += 1
                        except Exception as e:
                            if STATE["active"]:
                                print(f"⚠️ [ENGINE] Send error: {e}")
                            break
                    
                    # Debug logging every 10 seconds
                    if time.time() - last_log > 10:
                        rms = audio.get_rms(data)
                        status = "🔇 Paused" if STATE["is_ai_active"] else "🎙️ Streaming"
                        print(f"📊 [DEBUG] {status} | Sent: {chunks_sent} | RMS: {rms:.4f}")
                        chunks_sent = 0
                        last_log = time.time()
                    
                    elapsed = time.perf_counter() - t_start
                    await asyncio.sleep(max(0, chunk_duration - elapsed))

            async def receive_loop():
                """Handles incoming messages from Gemini - runs forever until session closes"""
                try:
                    async for response in session.receive():
                        if not STATE["active"]:
                            break  # Only break if user requested exit
                        
                        # Handle server_content
                        if response.server_content:
                            content = response.server_content
                            
                            if content.model_turn:
                                STATE["is_ai_active"] = True
                                for part in content.model_turn.parts:
                                    if part.inline_data:
                                        await audio.playback_queue.put(part.inline_data.data)
                                    if part.text:
                                        print(f"🤖 Jarvis: {part.text}")
                            
                            if content.turn_complete:
                                STATE["is_ai_active"] = False
                                # Set cooldown to prevent echo/false interruptions
                                STATE["cooldown_until"] = time.time() + 0.8  # 800ms cooldown
                                print("🎧 [ENGINE] Listening...")
                                # DO NOT BREAK - continue the loop!
                                continue
                            
                            if content.interrupted:
                                STATE["is_ai_active"] = False
                                # Clear playback queue but DON'T exit
                                while not audio.playback_queue.empty():
                                    try:
                                        audio.playback_queue.get_nowait()
                                    except asyncio.QueueEmpty:
                                        break
                                print("🚨 [ENGINE] Interrupted - Listening...")
                                continue  # Keep listening
                            
                            # Transcriptions (for debugging/logging)
                            if hasattr(content, 'input_transcription') and content.input_transcription:
                                if content.input_transcription.text:
                                    text = content.input_transcription.text.strip()
                                    if text:
                                        print(f"👤 You: {text}")
                                        
                            if hasattr(content, 'output_transcription') and content.output_transcription:
                                if content.output_transcription.text:
                                    # Already printed from inline_data, skip to avoid duplication
                                    pass
                        
                        # Handle tool calls
                        if response.tool_call:
                            function_responses = []
                            
                            for fc in response.tool_call.function_calls:
                                print(f"🛠️ [TOOL] Executing: {fc.name}")
                                
                                # Execute the function
                                result = execute_tool(fc.name, fc.args)
                                
                                # Build response
                                function_responses.append(
                                    types.FunctionResponse(
                                        id=fc.id,
                                        name=fc.name,
                                        response={"result": result}
                                    )
                                )
                            
                            # Send results back to Gemini
                            await session.send_tool_response(function_responses=function_responses)
                        
                        # Handle session resumption updates
                        if response.session_resumption_update:
                            new_handle = response.session_resumption_update.new_handle
                            if new_handle:
                                STATE["session_handle"] = new_handle
                                print("📝 [ENGINE] Session handle updated")
                        
                        # Handle GoAway (server wants us to reconnect)
                        if response.go_away:
                            print("⚠️ [ENGINE] Server requested reconnection")
                            break  # Reconnect with handle
                            
                except Exception as e:
                    if STATE["active"]:
                        print(f"❌ [ENGINE] Receive error: {e}")

            send_task = asyncio.create_task(send_loop())
            receive_task = asyncio.create_task(receive_loop())
            
            # Wait for either to complete (or error)
            _done, pending = await asyncio.wait(
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
            print("🛑 [ENGINE] Session conflict. Rotating key...")
            STATE["key_cooldowns"][STATE["key_idx"]] = time.time()
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            # Clear invalid session handle
            STATE["session_handle"] = None
            return True
        elif "1008" in err_msg:
            print("❌ [ENGINE] Invalid model or config: " + err_msg[:100])
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
    
    # Check if voice change was requested
    if STATE.get("needs_voice_change"):
        STATE["needs_voice_change"] = False
        print(f"🎵 [SYSTEM] Reconnecting with new voice: {STATE['voice']}")
        return True  # Trigger reconnect with new voice
        
    return False

async def main():
    print("🤖 JARVIS Voice Assistant Starting...")
    print(f"📍 Model: {MODEL}")
    print(f"🎵 Voice: {get_current_voice()}")
    print("💡 Tip: Speak naturally. Say 'exit' to quit.\n")
    
    retry_count = 0
    max_retries = 3
    
    while STATE["active"]:
        try:
            restart_needed = await start_session()
            
            if restart_needed:
                retry_count += 1
                if retry_count >= max_retries and not STATE.get("needs_voice_change"):
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
