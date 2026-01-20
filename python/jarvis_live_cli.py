import asyncio
import sys
import os
import pyaudio
import time
import numpy as np
import signal
import atexit
import uuid
from google import genai
from google.genai import types
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box
from core.config import API_KEYS, MODELS, AUDIO, SYSTEM_PROMPT_TEMPLATE, VOICE_MAPPINGS
from core.memory import (
    init_database, 
    get_facts_for_prompt, 
    get_preferences_for_prompt,
    get_preference,
    set_preference
)
from tools.tool_registry import TOOLS

# --- UI CONSTANTS ---
console = Console()

class JarvisUI:
    @staticmethod
    def banner():
        title = Text("JARVIS V3", style="bold cyan", justify="center")
        subtitle = Text("Advanced Live Voice Interface", style="italic blue", justify="center")
        banner = Panel(
            Text.assemble(title, "\n", subtitle),
            box=box.DOUBLE,
            border_style="bright_blue",
            padding=(1, 2)
        )
        console.print(banner)

    @staticmethod
    def info(msg):
        console.print(f"[bold cyan]ℹ️ [INFO][/bold cyan] {msg}")

    @staticmethod
    def engine(msg):
        console.print(f"[bold blue]📡 [ENGINE][/bold blue] {msg}")

    @staticmethod
    def tool(msg):
        console.print(f"[bold yellow]🛠️ [TOOL][/bold yellow] {msg}")

    @staticmethod
    def system(msg):
        console.print(f"[bold green]🧹 [SYSTEM][/bold green] {msg}")

    @staticmethod
    def error(msg):
        console.print(f"[bold red]❌ [ERROR][/bold red] {msg}")

    @staticmethod
    def debug(msg):
        # Only print debug if needed, keeping it subtle
        console.print(f"[dim white]📊 [DEBUG][/dim white] {msg}")

    @staticmethod
    def user(msg):
        console.print(f"\n[bold green]👤 You:[/bold green] [white]{msg}[/white]")

    @staticmethod
    def ai(msg):
        console.print(f"[bold cyan]🤖 Jarvis:[/bold cyan] [bright_white]{msg}[/bright_white]")

UI = JarvisUI()

# --- HISTORY MANAGEMENT ---
class HistoryManager:
    def __init__(self, max_turns=20):
        self.history = []  # List of {"role": str, "text": str}
        self.max_turns = max_turns

    def add_turn(self, role, text):
        if not text: return
        # Avoid duplicate consecutive entries if needed, but for now just append
        self.history.append({"role": role, "text": text})
        if len(self.history) > self.max_turns:
            self.history.pop(0)

    def get_context_string(self):
        if not self.history:
            return ""
        
        lines = ["\n[RECENT CONVERSATION HISTORY (Session Restored)]"]
        for turn in self.history:
            lines.append(f"{turn['role']}: {turn['text']}")
        lines.append("[End of History]\n")
        return "\n".join(lines)

HISTORY = HistoryManager()

# Initialize database
try:
    init_database()
except Exception as e:
    UI.error(f"Database initialization failed: {e}")

# --- GLOBAL STATE ---
KEYS = API_KEYS.gemini_keys
if not KEYS:
    UI.error("Critical: No API keys found in .env.")
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
    "audio": None,  # Current audio instance
}

_cleanup_done = False

# --- TOOL DEFINITIONS ---
def get_gemini_tools():
    """Build tool declarations from registry + local tools"""
    declarations = [
        types.FunctionDeclaration(
            name="exit_jarvis",
            description="Exit and close Jarvis when user says goodbye, exit, quit, or stop",
            parameters=types.Schema(type=types.Type.OBJECT, properties={})
        ),
        types.FunctionDeclaration(
            name="change_voice",
            description="Change Jarvis voice.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "voice_name": types.Schema(
                        type=types.Type.STRING,
                        description="Voice name: Puck, Charon, Fenrir, Aoede, Kore",
                        enum=["Puck", "Charon", "Fenrir", "Aoede", "Kore"]
                    )
                },
                required=["voice_name"]
            )
        )
    ]
    
    # Add from registry
    for name, info in TOOLS.items():
        if name in ["exit_jarvis", "change_voice"]: continue
        
        props = {}
        required = []
        for p_name, p_desc in info.get("parameters", {}).items():
            props[p_name] = types.Schema(type=types.Type.STRING, description=p_desc)
            required.append(p_name)
            
        declarations.append(
            types.FunctionDeclaration(
                name=name,
                description=info["description"],
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=props,
                    required=required
                )
            )
        )
    return declarations

JARVIS_TOOLS = get_gemini_tools()

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
                    UI.error(f"Playback error: {e}")
                    if consecutive_errors >= 5:
                        UI.error("Too many consecutive errors, stopping playback")
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
        except Exception:
            pass
        self.pya.terminate()

# --- VOICE MANAGEMENT ---
def get_current_voice():
    """Get the current voice preference"""
    return STATE.get("voice") or get_preference("voice") or AUDIO.default_voice

# --- TOOL EXECUTION ---
def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return result string"""
    try:
        if name == "exit_jarvis":
            STATE["active"] = False
            return "Goodbye! Jarvis is shutting down."
        
        elif name == "change_voice":
            new_voice = args.get("voice_name", "Puck")
            STATE["voice"] = new_voice
            set_preference("voice", new_voice)
            STATE["needs_voice_change"] = True
            return f"Switching to {new_voice} voice. One moment..."
        
        elif name in TOOLS:
            fn = TOOLS[name]["function"]
            # Convert numeric strings to numbers if they look like it
            clean_args = {}
            for k, v in args.items():
                if isinstance(v, str):
                    if v.isdigit():
                        clean_args[k] = int(v)
                    else:
                        try:
                            clean_args[k] = float(v)
                        except ValueError:
                            clean_args[k] = v
                else:
                    clean_args[k] = v
            
            result = fn(**clean_args)
            return str(result)
        
        return f"Unknown tool: {name}"
    except Exception as e:
        return f"Error executing {name}: {str(e)}"

# --- CONVERSATION MEMORY ---
def build_system_prompt(recent_context=None):
    """Build system prompt with user facts, preferences, and optional injected history"""
    user_facts = get_facts_for_prompt()
    user_preferences = get_preferences_for_prompt()
    
    return SYSTEM_PROMPT_TEMPLATE.format(
        user_facts=user_facts if user_facts else "",
        user_preferences=user_preferences if user_preferences else "",
        recent_context=recent_context or ""
    )

# --- SESSION LOGIC ---
async def start_session():
    session_id = str(uuid.uuid4())[:8]
    audio = UltraAudio()
    STATE["audio"] = audio
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
            UI.info(f"Key {current_k_idx+1} on cooldown. Skipping.")
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            continue
        all_on_cooldown = False
        break
    
    if all_on_cooldown:
        UI.error("All keys on cooldown. Waiting 10 seconds...")
        await asyncio.sleep(10)
        STATE["key_cooldowns"].clear()
    
    key = KEYS[STATE["key_idx"]]
    current_voice = get_current_voice()
    
    # Show connection info
    if STATE.get("session_handle"):
        UI.engine(f"Session {session_id}: Resuming with voice '{current_voice}'...")
    else:
        UI.engine(f"Session {session_id}: New session with voice '{current_voice}'...")
    
    # Inject history if this is a fresh session (or resumption failed previously)
    history_context = ""
    if not STATE.get("session_handle"):
        history_context = HISTORY.get_context_string()
        if history_context:
            UI.info("Injecting recent conversation history...")

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
        media_resolution="MEDIA_RESOLUTION_MEDIUM",
        
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
        
        system_instruction=build_system_prompt(recent_context=history_context)
    )

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            UI.engine(f"Session {session_id}: Linked.")
            UI.info("Listening (speak naturally)...")
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
                                UI.error(f"Send error: {e}")
                            break
                    
                    # Debug logging every 10 seconds
                    if time.time() - last_log > 5:
                        rms = audio.get_rms(data)
                        status = "AI SPEAKING" if STATE["is_ai_active"] else "LISTENING"
                        if current_time <= STATE["cooldown_until"]:
                            status = "COOLDOWN"
                        UI.debug(f"{status} | RMS: {rms:.4f}")
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
                            STATE["last_ai_activity"] = time.time()
                            content = response.server_content
                            
                            if content.model_turn:
                                STATE["is_ai_active"] = True
                                for part in content.model_turn.parts:
                                    if part.inline_data:
                                        await audio.playback_queue.put(part.inline_data.data)
                                    if part.text:
                                        text = part.text.strip()
                                        if text:
                                            UI.ai(text)
                                            HISTORY.add_turn("Jarvis", text)
                            
                            if content.turn_complete:
                                STATE["is_ai_active"] = False
                                STATE["cooldown_until"] = time.time() + 0.8
                                UI.info("Listening...")
                                continue
                            
                            if content.interrupted:
                                STATE["is_ai_active"] = False
                                while not audio.playback_queue.empty():
                                    try: audio.playback_queue.get_nowait()
                                    except asyncio.QueueEmpty: break
                                UI.info("Interrupted - Listening...")
                                continue
                            
                            # Transcriptions (for debugging/logging)
                            if hasattr(content, 'input_transcription') and content.input_transcription:
                                if content.input_transcription.text:
                                    text = content.input_transcription.text.strip()
                                    if text:
                                        UI.user(text)
                                        HISTORY.add_turn("User", text)
                                        
                            if hasattr(content, 'output_transcription') and content.output_transcription:
                                if content.output_transcription.text:
                                    # Already printed from inline_data, skip to avoid duplication
                                    pass
                        
                        # Handle tool calls
                        if response.tool_call:
                            STATE["last_ai_activity"] = time.time()
                            STATE["is_ai_active"] = True # Model is active while calling tools
                            function_responses = []
                            
                            for fc in response.tool_call.function_calls:
                                UI.tool(f"Executing: {fc.name}")
                                
                                try:
                                    # Execute the function
                                    result = execute_tool(fc.name, fc.args)
                                    UI.info(f"Result: {str(result)[:100]}...")
                                    
                                    # Build success response
                                    function_responses.append(
                                        types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={"result": result}
                                        )
                                    )
                                except Exception as e:
                                    # Build error response instead of crashing
                                    UI.error(f"Error executing {fc.name}: {e}")
                                    function_responses.append(
                                        types.FunctionResponse(
                                            id=fc.id,
                                            name=fc.name,
                                            response={"error": f"Tool execution failed: {str(e)}"}
                                        )
                                    )
                            
                            # Send results back to Gemini (even if errors occurred)
                            try:
                                await session.send_tool_response(function_responses=function_responses)
                                STATE["last_ai_activity"] = time.time()
                            except Exception as e:
                                UI.error(f"Failed to send tool response: {e}")
                                # Don't break - continue listening
                        
                        # Handle session resumption updates
                        if response.session_resumption_update:
                            new_handle = response.session_resumption_update.new_handle
                            if new_handle:
                                STATE["session_handle"] = new_handle
                                UI.info("Session handle updated for persistence.")
                        
                        # Handle GoAway (server wants us to reconnect)
                        if response.go_away:
                            UI.info("Server requested reconnection (GoAway)")
                            break  # Reconnect with handle
                            
                            
                except Exception as e:
                    UI.error(f"Receive loop error: {e}")
                    import traceback
                    traceback.print_exc()
                finally:
                     print("ℹ️ [DEBUG] Receive loop exited.")

            async def watchdog():
                """Ensures AI active flag doesn't get stuck"""
                while STATE["active"]:
                    await asyncio.sleep(5)
                    if STATE["is_ai_active"] and (time.time() - STATE.get("last_ai_activity", 0) > 10):
                        # print("🛡️ [WATCHDOG] Resetting AI active flag (stuck detected)")
                        STATE["is_ai_active"] = False

            send_task = asyncio.create_task(send_loop())
            receive_task = asyncio.create_task(receive_loop())
            watchdog_task = asyncio.create_task(watchdog())
            
            _done, pending = await asyncio.wait(
                [send_task, receive_task, watchdog_task],
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
            UI.error("Session conflict. Rotating key...")
            STATE["key_cooldowns"][STATE["key_idx"]] = time.time()
            STATE["key_idx"] = (STATE["key_idx"] + 1) % len(KEYS)
            # Clear invalid session handle
            STATE["session_handle"] = None
            return True
        elif "1008" in err_msg:
            UI.error(f"Invalid model or config: {err_msg[:100]}")
            return False
        else:
            UI.error(f"Engine Exception: {err_msg[:100]}")
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
    
    # Check if voice change was requested
    if STATE.get("needs_voice_change"):
        STATE["needs_voice_change"] = False
        UI.info(f"Reconnecting with new voice: {STATE['voice']}")
        return True  # Trigger reconnect with new voice
        
    return False

# --- CLEANUP HANDLERS ---
def cleanup():
    """Cleanup function called on exit"""
    global _cleanup_done
    if _cleanup_done:
        return
    _cleanup_done = True
    UI.system("Cleaning up resources...")
    STATE["active"] = False
    if STATE.get("audio"):
        STATE["audio"].close()
        STATE["audio"] = None

def signal_handler(sig, frame):
    """Forceful yet clean exit to prevent hanging audio threads"""
    console.print("\n[bold red]🛑 [SIGNAL] Interrupt received. Shutting down...[/bold red]")
    cleanup()
    os._exit(0)

# Register handlers
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def main():
    UI.banner()
    UI.info(f"Model: [bold white]{MODEL}[/bold white]")
    UI.info(f"Voice: [bold white]{get_current_voice()}[/bold white]")
    UI.info("Tip: Speak naturally. Say 'exit' to quit.\n")
    
    retry_count = 0
    max_retries = 3
    
    while STATE["active"]:
        try:
            restart_needed = await start_session()
            
            if not STATE["active"]:
                break
                
            if restart_needed:
                retry_count += 1
                if retry_count >= max_retries and not STATE.get("needs_voice_change"):
                    UI.error("Max retries reached. Exiting...")
                    break
                await asyncio.sleep(1)
            else:
                retry_count = 0
                if STATE["active"]:
                    UI.info("Session ended. Reconnecting...")
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            if STATE["active"]:
                UI.error(f"Unexpected error in main loop: {e}")
                await asyncio.sleep(2)
    
    # Final cleanup ensuring all tasks are dead
    # The cleanup() function registered with atexit will handle final shutdown messages.

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        cleanup()
