
import asyncio
import uuid
import time
import os
import signal
import sys
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
from tools.tool_registry import TOOLS

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
                     if self.running: print(f"Audio Write Error: {e}")
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
        self.state["active"] = True
        
        while self.state["active"]:
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
                speech_config = types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=current_voice)
                    )
                )

                config = types.LiveConnectConfig(
                    response_modalities=["AUDIO"],
                    speech_config=speech_config,
                    session_resumption=types.SessionResumptionConfig(handle=self.state.get("session_handle")),
                    tools=[types.Tool(google_search=types.GoogleSearch()), types.Tool(function_declarations=self._tools)],
                    system_instruction=self._build_system_prompt(recent_context=history_context)
                )

                self._update_status("CONNECTING")
                async with client.aio.live.connect(model=self.model, config=config) as session:
                    self._update_status("LISTENING")
                    self.state["is_ai_active"] = False
                    
                    worker_task = asyncio.create_task(audio.playback_worker(lambda: self.state["active"]))
                    
                    async def send_loop():
                        while self.state["active"]:
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
                                    print(f"Send error: {e}")
                                    break
                            await asyncio.sleep(0.01)

                    async def receive_loop():
                        try:
                            async for response in session.receive():
                                if not self.state["active"]: break
                                
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
                                        res = self._execute_tool(fc.name, fc.args)
                                        fn_responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response={"result": res}))
                                    await session.send_tool_response(function_responses=fn_responses)

                                if response.session_resumption_update:
                                    if response.session_resumption_update.new_handle:
                                        self.state["session_handle"] = response.session_resumption_update.new_handle
                        except Exception as e:
                            print(f"Receive loop error: {e}")

                    send_task = asyncio.create_task(send_loop())
                    receive_task = asyncio.create_task(receive_loop())
                    
                    await asyncio.wait([send_task, receive_task], return_when=asyncio.FIRST_COMPLETED)
                    
                    # Cleanup tasks
                    for t in [send_task, receive_task, worker_task]:
                        t.cancel()
                        try:
                            await t
                        except (asyncio.CancelledError, Exception):
                            pass
                
            except Exception as e:
                print(f"Session error: {e}")
                self._update_status("ERROR", str(e))
                await asyncio.sleep(2)

            finally:
                # Close client explicitly
                try:
                    if hasattr(client, 'aio') and hasattr(client.aio, 'aclose'):
                        # Await the coroutine explicitly
                        await client.aio.aclose()
                    elif hasattr(client, 'close'):
                        client.close()
                except Exception as e:
                    print(f"Cleanup error (client): {e}")
                
                # Small yield to let loop settle
                await asyncio.sleep(0.1)
            
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
                # Use asyncio.run for cleaner loop management and cleanup
                asyncio.run(self._session_loop())
            except Exception as e:
                print(f"Loop crash: {e}")
            finally:
                self.thread = None

        self.thread = threading.Thread(target=run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """Signals the session to stop and waits for it"""
        self.state["active"] = False
        # Do not join() in the main thread if possible, as it blocks rumps UI.
        # But for 'exit_jarvis' tool, it's called from within the loop thread.
        # So we just set the flag and let _session_loop reach its end.
        pass
