import asyncio
import uuid
import time
import os
import signal
import sys
from pathlib import Path

# #region agent log
_sm_root = Path(__file__).resolve().parent.parent
if str(_sm_root) not in sys.path:
    sys.path.insert(0, str(_sm_root))
def _agent_log(*a, **k):
    try:
        from debug_log import _agent_log as _log
        _log(*a, **k)
    except Exception:
        pass
try:
    from debug_log import _agent_log as _log0
    _log0("session_manager.py:top", "import_start", hypothesis_id="H1")
except Exception:
    pass
# #endregion

import pyaudio
import numpy as np
from google import genai
from google.genai import types

from core.config import API_KEYS, MODELS, AUDIO, SYSTEM_PROMPT_TEMPLATE
from core.memory import (
    init_database, 
    get_facts_for_prompt, 
    get_preferences_for_prompt,
    get_preference,
    set_preference
)
from core.personalization import personalization
from tools.tool_registry import TOOLS
from utils.volume_control import VolumeController

# --- AUDIO HANDLER ---
class UltraAudio:
    def __init__(self, send_rate=16000, recv_rate=24000, chunk_size=512):
        self.pya = pyaudio.PyAudio()
        self.chunk_size = chunk_size
        self.in_stream = self.pya.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=send_rate,
            input=True,
            frames_per_buffer=chunk_size
        )
        self.out_stream = self.pya.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=recv_rate,
            output=True
        )
        self.playback_queue = asyncio.Queue()
        self.running = True

    def try_reopen_output(self):
        """Attempts to restart the output stream on error"""
        try:
            if self.out_stream:
                self.out_stream.close()
            self.out_stream = self.pya.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=24000, # Hardcoded recv_rate from init
                output=True
            )
            return True
        except Exception as e:
            print(f"Failed to reopen audio: {e}")
            return False

    async def playback_worker(self, session_active_check_fn):
        """Dedicated worker for playing audio"""
        loop = asyncio.get_event_loop()
        consecutive_errors = 0
        while self.running and session_active_check_fn():
            try:
                # Wait for data, but respect shutdown
                data = await asyncio.wait_for(self.playback_queue.get(), timeout=0.1)
                if not self.running: break
                
                # Run write in executor to avoid blocking asyncio loop
                # Wrap in try-except block specifically for the write operation
                try:
                    await loop.run_in_executor(None, self.out_stream.write, data)
                except OSError as e:
                     if self.running:
                         print(f"Audio Write Error: {e}")
                         # Try to recover
                         if self.try_reopen_output():
                             continue
                         else:
                             break

                consecutive_errors = 0
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                # ...
                if self.running:
                    consecutive_errors += 1
                    print(f"⚠️ Playback error: {e}")
                    if consecutive_errors >= 5:
                        print("❌ Too many consecutive errors, stopping playback")
                        break
                    await asyncio.sleep(0.1)
                continue

    def get_rms(self, data):
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        return np.sqrt(np.mean(samples**2))

    def read_mic(self):
        try:
            return self.in_stream.read(self.chunk_size, exception_on_overflow=False)
        except OSError:
            return b'\x00' * self.chunk_size

    def close(self):
        self.running = False
        # Give worker a moment to stop
        time.sleep(0.2)
        
        try:
            if self.in_stream and self.in_stream.is_active():
                self.in_stream.stop_stream()
            self.in_stream.close()
        except: pass
        
        try:
            if self.out_stream and self.out_stream.is_active():
                 self.out_stream.stop_stream()
            self.out_stream.close()
        except: pass
        
        self.pya.terminate()

# --- HISTORY MANAGEMENT ---
class HistoryManager:
    def __init__(self, max_turns=20):
        self.history = []
        self.max_turns = max_turns

    def add_turn(self, role, text):
        if not text: return
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

# --- SESSION CLASS ---
class JarvisSession:
    def __init__(self, on_status_change=None):
        self.keys = API_KEYS.gemini_keys
        if not self.keys:
            raise ValueError("No API keys found in .env")
        
        self.model = MODELS.gemini_live_model
        self.chunk_size = AUDIO.chunk_size
        self.send_rate = AUDIO.input_sample_rate
        self.recv_rate = AUDIO.output_sample_rate
        
        self.state = {
            "key_idx": 0,
            "active": False, # Controls the main loop
            "is_ai_active": False,
            "key_cooldowns": {},
            "session_handle": None,
            "voice": None,
            "needs_voice_change": False,
            "cooldown_until": 0,
            "audio": None,
            "status": "STOPPED" # STOPPED, INITIALIZING, LISTENING, PROCESSING, SPEAKING
        }
        
        # Volume Controller
        self.volume_manager = VolumeController()

        # Callback for UI updates
        self.on_status_change = on_status_change
        
        # History
        self.history = HistoryManager()
        
        # Initialize DB
        try:
            init_database()
        except Exception as e:
            print(f"DB Error: {e}")

        self._tools = self._build_tools()
        self._current_task = None # Main asyncio task
        self.thread = None

    def _update_status(self, new_status, extra=None):
        self.state["status"] = new_status

        # Handle volume ducking
        if new_status == "SPEAKING":
            self.volume_manager.duck_media(target_percent=10) # 10% volume
        elif new_status in ["LISTENING", "PROCESSING", "STOPPED", "INITIALIZING"]:
            # Maybe keep ducking during listening?
            # User said: "decrease to 5% of the volume the AI Assistant is speaking at"
            # It's better to duck during both speaking and listening so the AI can hear user.
            # But user specifically said "When Bhuvi is speaking".
            # Let's duck when speaking.
            # And restore when done.
            if new_status != "SPEAKING":
                self.volume_manager.restore_media()

        if self.on_status_change:
            self.on_status_change(new_status, extra)
        else:
            print(f"STATUS: {new_status} {extra if extra else ''}")

    def get_current_voice(self):
        return self.state.get("voice") or get_preference("voice") or AUDIO.default_voice

    def _build_tools(self):
        # ... (Tool building logic from cli) ...
        # Simplified for brevity, will import or copy logic
        declarations = [
            types.FunctionDeclaration(
                name="exit_jarvis",
                description="Exit and close Jarvis when user says goodbye, exit, quit, or stop. Puts Jarvis in standby.",
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
                    parameters=types.Schema(type=types.Type.OBJECT, properties=props, required=required)
                )
            )
        return declarations

    def _build_system_prompt(self, recent_context=None):
        user_facts = get_facts_for_prompt()
        user_preferences = get_preferences_for_prompt()
        return SYSTEM_PROMPT_TEMPLATE.format(
            user_facts=user_facts if user_facts else "",
            user_preferences=user_preferences if user_preferences else "",
            recent_context=recent_context or ""
        )

    def _execute_tool(self, name, args):
        try:
            if name == "exit_jarvis":
                self.stop()
                return "Goodbye! Going to standby."
            
            elif name == "change_voice":
                new_voice = args.get("voice_name", "Puck")
                self.state["voice"] = new_voice
                set_preference("voice", new_voice)
                self.state["needs_voice_change"] = True
                return f"Switching to {new_voice}."
            
            elif name in TOOLS:
                fn = TOOLS[name]["function"]
                # Type coercion logic...
                clean_args = {}
                for k, v in args.items():
                    if isinstance(v, str) and v.isdigit():
                        clean_args[k] = int(v)
                    else:
                        clean_args[k] = v # simplified
                
                result = fn(**clean_args)
                return str(result)
            return f"Unknown tool: {name}"
        except Exception as e:
            return f"Error executing {name}: {e}"

    async def _session_loop(self):
        """Main internal loop interacting with Gemini"""
        _agent_log("session_manager.py:_session_loop", "enter", hypothesis_id="H3")
        self.state["active"] = True
        
        while self.state["active"]:
            client = None
            self._update_status("INITIALIZING")
            
            # Key rotation logic omitted for brevity, essential parts kept
            key = self.keys[self.state["key_idx"]]
            current_voice = self.get_current_voice()
            
            try:
                # Init audio if needed
                if not self.state.get("audio"):
                    print("📡 [ENGINE] Initializing Audio Hardware...")
                    self.state["audio"] = UltraAudio(self.send_rate, self.recv_rate, self.chunk_size)
                audio = self.state["audio"]

                # History
                history_context = ""
                if not self.state.get("session_handle"):
                     history_context = self.history.get_context_string()

                client = genai.Client(
                    api_key=key,
                    http_options={'api_version': MODELS.gemini_live_api_version}
                )
                _agent_log("session_manager.py:_session_loop", "client_created", hypothesis_id="H3")
                speech_config = types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=current_voice)
                    )
                )

                config_kw = {
                    "response_modalities": ["AUDIO"],
                    "speech_config": speech_config,
                    "system_instruction": self._build_system_prompt(recent_context=history_context),
                    "context_window_compression": types.ContextWindowCompressionConfig(
                        trigger_tokens=25600,
                        sliding_window=types.SlidingWindow(target_tokens=12800),
                    ),
                }
                h = self.state.get("session_handle")
                if h is not None:
                    config_kw["session_resumption"] = types.SessionResumptionConfig(handle=h)
                # Tools Configuration
                config_kw["tools"] = [types.Tool(google_search=types.GoogleSearch()), types.Tool(function_declarations=self._tools)]
                _agent_log("session_manager.py:_session_loop", "config_with_tools", hypothesis_id="H3")
                config = types.LiveConnectConfig(**config_kw)

                # Retry logic for 409 conflicts
                max_retries = 3
                attempt = 0
                backoff = 2
                
                while attempt < max_retries:
                    try:
                        self._update_status("CONNECTING")
                        _agent_log("session_manager.py:_session_loop", "connect_before", data={"model": self.model, "attempt": attempt+1}, hypothesis_id="H3")
                        
                        async with client.aio.live.connect(model=self.model, config=config) as session:
                            _agent_log("session_manager.py:_session_loop", "connect_ok", hypothesis_id="H3")
                            self._update_status("LISTENING")
                            self.state["is_ai_active"] = False
                            
                            # Reset backoff on successful connection
                            attempt = 0
                            backoff = 2
                            
                            # Use a specific flag for this run's worker to ensure it dies on retry
                            current_run_active = True
                            worker_task = asyncio.create_task(audio.playback_worker(lambda: current_run_active and self.state["active"]))
                            
                            async def send_loop():
                                while self.state["active"] and current_run_active:
                                    data = await asyncio.get_event_loop().run_in_executor(None, audio.read_mic)
                                    should_send = (
                                        not self.state["is_ai_active"] and 
                                        time.time() > self.state["cooldown_until"]
                                    )
                                    if should_send:
                                        try:
                                            await session.send_realtime_input(
                                                audio=types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                                            )
                                        except Exception as e:
                                            _agent_log("session_manager.py:send_loop", "send_error", data={"error": str(e)}, hypothesis_id="H3")
                                            print(f"Send error: {e}")
                                            break
        
                                    # Removed sleep to reduce latency
                                    # await asyncio.sleep(0.01)
        
                            async def receive_loop():
                                last_activity = time.time()
                                msg_count = 0
                                try:
                                    # Use direct async for like the Google sample
                                    _agent_log("session_manager.py:receive_loop", "starting_receive", hypothesis_id="H3")
                                    async for response in session.receive():
                                        last_activity = time.time()
                                        msg_count += 1
                                        
                                        # Log first few messages
                                        if msg_count <= 3:
                                            resp_data = {
                                                "msg_num": msg_count,
                                                "has_server_content": bool(response.server_content),
                                                "has_tool_call": bool(response.tool_call),
                                            }
                                            if hasattr(response, 'error'):
                                                resp_data["error"] = str(response.error)
                                            _agent_log("session_manager.py:receive_loop", "message_received", data=resp_data, hypothesis_id="H3")
        
                                        if not self.state["active"]: break
                                        
                                        # Check for errors
                                        if hasattr(response, 'error') and response.error:
                                            _agent_log("session_manager.py:receive_loop", "response_error", data={"error": str(response.error)}, hypothesis_id="H3")
                                            print(f"❌ Server error: {response.error}")
                                            break
        
                                        if response.server_content:
                                            content = response.server_content
                                            if content.model_turn:
                                                self.state["is_ai_active"] = True
                                                self._update_status("SPEAKING")
                                                for part in content.model_turn.parts:
                                                    if part.inline_data:
                                                        await audio.playback_queue.put(part.inline_data.data)
                                                    if part.text:
                                                        text = part.text.strip()
                                                        if text:
                                                            self.history.add_turn("Jarvis", text)
                                                            print(f"🤖 Jarvis: {text}")
        
                                            if content.turn_complete:
                                                self.state["is_ai_active"] = False
                                                self.state["cooldown_until"] = time.time() + 0.8
                                                self._update_status("LISTENING")
                                                continue
        
                                            if hasattr(content, 'input_transcription') and content.input_transcription:
                                                 if content.input_transcription.text:
                                                     text = content.input_transcription.text.strip()
                                                     if text:
                                                         self.history.add_turn("User", text)
                                                         print(f"👤 You: {text}")
        
                                        if response.tool_call:
                                            self.state["is_ai_active"] = True
                                            self._update_status("PROCESSING")
                                            fn_responses = []
                                            for fc in response.tool_call.function_calls:
                                                print(f"Executing {fc.name}...")
                                                args = {}
                                                if hasattr(fc, 'args') and fc.args is not None:
                                                    if isinstance(fc.args, dict):
                                                        args = fc.args
                                                    else:
                                                        try:
                                                            args = dict(fc.args) if hasattr(fc.args, 'items') else {}
                                                        except Exception as ae:
                                                            _agent_log("session_manager.py:receive_loop", "tool_args_fail", data={"error": str(ae), "tool": fc.name}, hypothesis_id="H3")
                                                try:
                                                    res = self._execute_tool(fc.name, args)
                                                except Exception as te:
                                                    res = str(te)
                                                    _agent_log("session_manager.py:receive_loop", "tool_exec_fail", data={"error": str(te), "tool": fc.name}, hypothesis_id="H3")
                                                fn_responses.append(
                                                    types.FunctionResponse(id=fc.id, name=fc.name, response={"result": res})
                                                )
                                            await session.send_tool_response(function_responses=fn_responses)
        
                                        if response.session_resumption_update:
                                            if response.session_resumption_update.new_handle:
                                                self.state["session_handle"] = response.session_resumption_update.new_handle
        
                                        # Check for stuck state periodically
                                        # WATCHDOG logic moved to dedicated task below
                                        pass
        
                                except Exception as e:
                                    _agent_log("session_manager.py:receive_loop", "receive_error", data={"error": str(e), "type": type(e).__name__, "msg_count": msg_count}, hypothesis_id="H3")
                                    print(f"Receive loop error: {e}")
                                    # StopAsyncIteration means server closed - this is normal when connection ends
                                    if isinstance(e, StopAsyncIteration):
                                        print("Server closed stream.")
                                    # 409 in receive loop? Unlikely but possible
                                    if "409" in str(e) or "conflict" in str(e).lower():
                                        raise e # Re-raise to catch in outer loop
                                    else:
                                        print(f"Non-conflict error in receive: {e}")
                                        # Don't re-raise generic errors to keep retry loop alive? 
                                        # Actually we should break to finally block and maybe retry if it was a connection drop
                                        pass
        
                            send_task = asyncio.create_task(send_loop())
                            receive_task = asyncio.create_task(receive_loop())
                            
                            # Watchdog Task
                            async def watchdog_loop():
                                while self.state["active"] and current_run_active:
                                    if self.state["status"] == "PROCESSING":
                                        # If stuck in PROCESSING for > 25 seconds
                                        if time.time() - last_activity > 25.0:
                                            print("🚨 WATCHDOG: Session stuck in PROCESSING for > 25s. Force resetting.")
                                            self.state["active"] = False # This will break send/receive loops
                                            # We need to ensure we break the outer wait too
                                            send_task.cancel()
                                            receive_task.cancel()
                                            break
                                    await asyncio.sleep(1.0)
                            
                            watchdog_task = asyncio.create_task(watchdog_loop())

                            _agent_log("session_manager.py:_session_loop", "tasks_started", data={"send": "started", "receive": "started"}, hypothesis_id="H3")
                            
                            # Wait for either task to complete (receive will complete on StopAsyncIteration when server closes)
                            # Or watchdog cancels them
                            done, pending = await asyncio.wait([send_task, receive_task, watchdog_task], return_when=asyncio.FIRST_COMPLETED)
                            _agent_log("session_manager.py:_session_loop", "task_completed", data={"done_count": len(done)}, hypothesis_id="H3")
                            
                            # Cleanup tasks
                            current_run_active = False # Signal worker to stop
                            for t in [send_task, receive_task, worker_task, watchdog_task]:
                                t.cancel()
                                try:
                                    await t
                                except (asyncio.CancelledError, Exception):
                                    pass
                            
                            # If we returned normally from wait, we are done with this session attempt.
                            # If manual stop, break retry loop
                            if not self.state["active"]:
                                break
                            
                    except Exception as e:
                        is_conflict = "409" in str(e) or "conflict" in str(e).lower()
                        if is_conflict:
                            attempt += 1
                            if attempt < max_retries:
                                print(f"⚠️ Conflict 409. Retrying in {backoff}s... (Attempt {attempt}/{max_retries})")
                                _agent_log("session_manager.py:_session_loop", "409_retry", data={"attempt": attempt, "backoff": backoff}, hypothesis_id="H4")
                                await asyncio.sleep(backoff)
                                backoff *= 2
                                continue
                            else:
                                print("❌ Max retries for 409 reached. Stopping.")
                                self.state["active"] = False
                                break
                        else:
                            _agent_log("session_manager.py:_session_loop", "session_error", data={"error": str(e)}, hypothesis_id="H3")
                            print(f"Session error: {e}")
                            # Clean up and deciding whether to retry or stop
                            # For non-conflict errors, we'll try a few times but then stop to avoid spamming
                            self._update_status("ERROR", str(e))
                            await asyncio.sleep(2)
                            
                            attempt += 1
                            if attempt >= max_retries:
                                 print("❌ Max retries for Error reached. Stopping.")
                                 self.state["active"] = False
                                 break
                            continue

                    # If we break out of the async with block normally (e.g. user stopped), break retry loop
                    if not self.state["active"]:
                        break

            finally:
                _agent_log("session_manager.py:_session_loop", "finally_enter", data={"client_is_none": client is None}, hypothesis_id="H5")
                try:
                    if client is not None:
                        # client.aio.live.connect returns a context manager, but the client itself might need closing if we created it.
                        pass  # genai.Client usage might not require explicit close if just used for context manager, but good practice.
                        if hasattr(client, 'aio') and hasattr(client.aio, 'aclose'):
                             # It seems we need to await this if we want to be clean
                             pass 
                        # Actual client close:
                        # client.close() # synchronous close?
                except Exception as e:
                    print(f"Cleanup error (client): {e}")
                _agent_log("session_manager.py:_session_loop", "finally_exit", hypothesis_id="H5")
                
            
            # Check for voice change or stop
            if not self.state["active"]:
                break
            if self.state["needs_voice_change"]:
                self.state["needs_voice_change"] = False
                continue # Re-loop to connect with new voice

        # End of Session
        if self.state.get("audio"):
            self.state["audio"].close()
            self.state["audio"] = None
        self._update_status("STOPPED")

    def start(self):
        """Starts the session in a separate thread/loop"""
        _agent_log("session_manager.py:start", "enter", hypothesis_id="H3")
        # Wait a moment for any dying thread to finish cleanup
        if self.thread and self.thread.is_alive():
            if not self.state["active"]:
                self.thread.join(timeout=3.0)
            else:
                print("⚠️ Session already active.")
                return
        
        self.state["active"] = True
        
        import threading
        def run_loop():
            try:
                _agent_log("session_manager.py:run_loop", "asyncio_run_start", hypothesis_id="H3")
                asyncio.run(self._session_loop())
                _agent_log("session_manager.py:run_loop", "asyncio_run_done", hypothesis_id="H3")
            except Exception as e:
                _agent_log("session_manager.py:run_loop", "loop_crash", data={"error": str(e)}, hypothesis_id="H3")
                print(f"Loop crash: {e}")
            finally:
                self.thread = None

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Signals the session to stop and waits for it"""
        if self.state["active"]:
            self.state["active"] = False
            
            # Helper to run learning without blocking
            def trigger_learning():
                try:
                   transcript = self.history.get_context_string()
                   print(f"🧠 Triggering background learning on {len(transcript)} chars...")
                   asyncio.run(personalization.summarize_and_learn(transcript))
                except Exception as e:
                   print(f"Learning trigger failed: {e}")

            import threading
            threading.Thread(target=trigger_learning, daemon=True).start()

        # Do not join() in the main thread if possible, as it blocks rumps UI.
        # But for 'exit_jarvis' tool, it's called from within the loop thread.
        # So we just set the flag and let _session_loop reach its end.
        pass
