try:
    import pyttsx3
except Exception:
    pyttsx3 = None
import subprocess
import tempfile
import os
import re
import time
import threading
import sys
import wave
try:
    import audioop
except Exception:
    try:
        import audioop_lts as audioop
    except Exception:
        audioop = None
try:
    from dotenv import load_dotenv
except Exception:
    def load_dotenv(*args, **kwargs):
        return None

# Load environment variables safely:
# 1) If JARVIS_DOTENV_PATH or DOTENV_PATH is set, load that file.
# 2) Else prefer .env.local, then .env in repo root.
def _load_env_files():
    try:
        # Allow user to point to an env file outside the repo
        custom_path = os.getenv('JARVIS_DOTENV_PATH') or os.getenv('DOTENV_PATH')
        if custom_path and os.path.isfile(custom_path):
            try:
                load_dotenv(dotenv_path=custom_path, override=False)
            except Exception:
                pass
            return
        # Fall back to local files in project root
        here = os.path.abspath(os.path.dirname(__file__))
        for name in ('.env.local', '.env'):
            path = os.path.join(here, name)
            if os.path.isfile(path):
                try:
                    load_dotenv(dotenv_path=path, override=False)
                except Exception:
                    pass
    except Exception:
        pass

_load_env_files()

# Optional: overlay UI state file for a separate macOS overlay app to read
import json as _json
OVERLAY_STATE_PATH = os.getenv('JARVIS_OVERLAY_STATE', '/tmp/jarvis_overlay_state.json')
SHOW_OVERLAY = (os.getenv('JARVIS_OVERLAY', '1') == '1')
OVERLAY_PROC = None  # background Cocoa overlay process

def _overlay_write(status: str, text: str = '', level: float = 0.0, visible: bool | None = None):
    if not SHOW_OVERLAY:
        return
    try:
        data = {"status": status, "text": (text or '')[:300], "level": float(max(0.0, min(1.0, level)))}
        if visible is not None:
            data["visible"] = bool(visible)
            if visible:
                _maybe_launch_overlay()
        with open(OVERLAY_STATE_PATH, 'w', encoding='utf-8') as f:
            _json.dump(data, f)
    except Exception:
        pass

def _maybe_launch_overlay():
    """Launch the Cocoa overlay app as a background process if enabled.
    Controlled by env JARVIS_OVERLAY_LAUNCH=1 (default 1)."""
    if not SHOW_OVERLAY or os.getenv('JARVIS_OVERLAY_LAUNCH', '1') != '1':
        return
    global OVERLAY_PROC
    try:
        if OVERLAY_PROC is not None and OVERLAY_PROC.poll() is None:
            return
    except Exception:
        pass
    try:
        here = os.path.abspath(os.path.dirname(__file__))
        script = os.path.join(here, 'ui', 'overlay_app.py')
        if os.path.isfile(script):
            OVERLAY_PROC = subprocess.Popen(
                [sys.executable, script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            # Prime initial idle state (hidden until explicitly shown)
            try:
                with open(OVERLAY_STATE_PATH, 'w', encoding='utf-8') as f:
                    _json.dump({"status": "idle", "text": "", "level": 0.0, "visible": False}, f)
            except Exception:
                pass
    except Exception:
        pass

def _maybe_quit_overlay():
    """Optionally terminate the overlay process when exiting.
    Controlled by env JARVIS_OVERLAY_AUTOQUIT=1 (default 0)."""
    if os.getenv('JARVIS_OVERLAY_AUTOQUIT', '0') != '1':
        return
    global OVERLAY_PROC
    try:
        if OVERLAY_PROC is not None and OVERLAY_PROC.poll() is None:
            try:
                OVERLAY_PROC.terminate()
                OVERLAY_PROC.wait(timeout=1.0)
            except Exception:
                try:
                    OVERLAY_PROC.kill()
                except Exception:
                    pass
    except Exception:
        pass

def _compute_wav_levels(path: str, frame_ms: int = 30) -> tuple[list[float], float]:
    """Compute a normalized RMS envelope from a WAV file.
    Returns (levels [0..1], frame_dt_seconds)."""
    levels: list[float] = []
    try:
        with wave.open(path, 'rb') as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            if framerate <= 0 or n_frames <= 0:
                return [], frame_ms / 1000.0
            win_frames = max(1, int(framerate * (frame_ms / 1000.0)))
            # Read chunk by chunk
            while True:
                data = wf.readframes(win_frames)
                if not data:
                    break
                # Convert to mono if needed
                if n_channels > 1 and audioop is not None:
                    try:
                        data_mono = audioop.tomono(data, sampwidth, 0.5, 0.5)
                    except Exception:
                        data_mono = data
                else:
                    data_mono = data
                try:
                    if audioop is not None:
                        rms = audioop.rms(data_mono, sampwidth)
                    else:
                        rms = 0
                except Exception:
                    rms = 0
                levels.append(float(rms))
            if not levels:
                return [], frame_ms / 1000.0
            # Normalize and lightly smooth
            peak = max(levels) or 1.0
            levels = [min(1.0, (v / peak) ** 0.9) for v in levels]
            # 3-tap moving average for smoother motion
            if len(levels) >= 3:
                smoothed = [levels[0]]
                for i in range(1, len(levels) - 1):
                    smoothed.append((levels[i - 1] + levels[i] + levels[i + 1]) / 3.0)
                smoothed.append(levels[-1])
                levels = smoothed
    except Exception:
        levels = []
    return levels, frame_ms / 1000.0

def _init_tts():
    # If pyttsx3 is not available in this environment, skip initializing
    if pyttsx3 is None:
        return None
    try:
        eng = pyttsx3.init(driverName='nsss')  # macOS native
    except Exception:
        try:
            eng = pyttsx3.init()  # fallback
        except Exception:
            return None
    try:
        rate_wpm = int(os.getenv('TTS_RATE_WPM', '200'))
        eng.setProperty('rate', rate_wpm)
        eng.setProperty('volume', 1.0)
        preferred = (os.getenv('TTS_VOICE') or '').lower()
        if preferred:
            for v in eng.getProperty('voices'):
                vid = (getattr(v, 'id', '') or '').lower()
                vname = (getattr(v, 'name', '') or '').lower()
                if preferred in vid or preferred in vname:
                    eng.setProperty('voice', getattr(v, 'id', None))
                    break
        else:
            # Prefer a natural male 'Alex' voice if available
            for v in eng.getProperty('voices'):
                vid = (getattr(v, 'id', '') or '').lower()
                vname = (getattr(v, 'name', '') or '').lower()
                if 'alex' in vid or 'alex' in vname:
                    eng.setProperty('voice', getattr(v, 'id', None))
                    break
    except Exception:
        pass
    return eng

engine = _init_tts()

# Global state for stoppable TTS playback (barge-in)
CURRENT_TTS_PROC = None
CURRENT_TTS_TMPFILE = None
CURRENT_TTS_LOCK = threading.Lock()

def stop_speaking():
    """Stop any ongoing TTS playback immediately and clean temp file."""
    global CURRENT_TTS_PROC, CURRENT_TTS_TMPFILE
    with CURRENT_TTS_LOCK:
        proc = CURRENT_TTS_PROC
        tmp = CURRENT_TTS_TMPFILE
        CURRENT_TTS_PROC = None
        CURRENT_TTS_TMPFILE = None
    try:
        if proc and proc.poll() is None:
            try:
                proc.terminate()
            except Exception:
                pass
            # Ensure process ends promptly
            try:
                proc.wait(timeout=1.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    except Exception:
        pass
    if tmp and os.path.exists(tmp):
        try:
            os.remove(tmp)
        except Exception:
            pass
    # Overlay: reset to idle when we forcibly stop
    _overlay_write('idle', '')

def _play_file_async(path: str, *, levels: list[float] | None = None, display_text: str | None = None, frame_dt: float = 0.03):
    """Play an audio file via afplay asynchronously and track process; delete on exit.
    If 'levels' is provided (0..1), update overlay level over time for a voice-reactive ring.
    """
    global CURRENT_TTS_PROC, CURRENT_TTS_TMPFILE
    # Stop any prior playback first to avoid overlaps
    stop_speaking()
    _overlay_write('speaking', (display_text or os.path.basename(path))[:300], 0.4)
    try:
        proc = subprocess.Popen(['afplay', path])
    except Exception:
        # As a fallback, try 'say' to at least speak file path text
        proc = None
    with CURRENT_TTS_LOCK:
        CURRENT_TTS_PROC = proc
        # Mark for deletion when finished (if in temp area)
        CURRENT_TTS_TMPFILE = path
    # Overlay: set speaking state
    _overlay_write('speaking', (display_text or os.path.basename(path))[:300], 0.4)
    # Background watcher to remove temp file and clear proc
    def _watch():
        global CURRENT_TTS_PROC, CURRENT_TTS_TMPFILE
        try:
            if proc is not None:
                proc.wait()
        except Exception:
            pass
        finally:
            with CURRENT_TTS_LOCK:
                # Only delete if it's still the current tmp (not replaced)
                tmp = CURRENT_TTS_TMPFILE
                CURRENT_TTS_PROC = None
                CURRENT_TTS_TMPFILE = None
            if tmp and os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass
            # Mark overlay idle after playback completes
            _overlay_write('idle', '')
    threading.Thread(target=_watch, daemon=True).start()

    # Optional animator for overlay level envelope
    if levels and proc is not None:
        token = id(proc)
        def _animate():
            i = 0
            n = len(levels)
            while i < n:
                with CURRENT_TTS_LOCK:
                    if CURRENT_TTS_PROC is None or id(CURRENT_TTS_PROC) != token:
                        break
                lvl = float(max(0.0, min(1.0, levels[i])))
                _overlay_write('speaking', (display_text or os.path.basename(path))[:300], lvl)
                i += 1
                try:
                    time.sleep(frame_dt)
                except Exception:
                    pass
        threading.Thread(target=_animate, daemon=True).start()


def _split_into_sentences(text: str) -> list[str]:
    try:
        parts = re.split(r"(?<=[.!?])\s+", text.strip())
        return [p.strip() for p in parts if p.strip()]
    except Exception:
        return [text]

def _yield_sentences_from_stream(chunks_iter):
    """Accumulate streamed text and yield full sentences as they form."""
    buf = ""
    for chunk in chunks_iter:
        buf += chunk
        # When we have a sentence end, emit complete sentences, keep remainder
        parts = re.split(r"(?<=[.!?])\s+", buf)
        # All but last are complete sentences
        for sent in parts[:-1]:
            s = sent.strip()
            if s:
                yield s
        buf = parts[-1]
    if buf.strip():
        yield buf.strip()


def _speak_maybe_chunked(text: str):
    """Speak in sentence chunks for lower latency when enabled.
    Controlled by env SPEAK_CHUNKED=1. Falls back to single speak otherwise.
    """
    if os.getenv('SPEAK_CHUNKED', '1') != '1':
        speak(text)
        return
    chunks = _split_into_sentences(text)
    # If very short or single chunk, speak normally
    if len(chunks) <= 1 or sum(len(c) for c in chunks) < 80:
        speak(text)
        return
    for i, sent in enumerate(chunks):
        if STOP_EVENT.is_set():
            break
        # Wait for any current speech to finish to avoid overlap/echo
        while is_speaking() and not STOP_EVENT.is_set():
            time.sleep(0.02)
            _overlay_write('speaking', sent, 0.4)
            speak(sent)
        # Small gap between sentences to avoid boundary clicks
        time.sleep(0.05)


def is_speaking() -> bool:
    """Return True if a TTS process is currently playing audio."""
    with CURRENT_TTS_LOCK:
        proc = CURRENT_TTS_PROC
    try:
        return bool(proc and proc.poll() is None)
    except Exception:
        return False

def _strip_emojis(s: str) -> str:
    # Basic emoji removal for better TTS pronunciation
    try:
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "]+",
            flags=re.UNICODE,
        )
        return emoji_pattern.sub("", s)
    except Exception:
        return s


def _clean_transcript(text: str) -> str:
    """Reduce common stutters/fillers and repeated words to improve intent clarity."""
    if not text:
        return text
    # Lowercase for filtering but preserve original case later if needed
    s = text
    # Remove common fillers as standalone tokens
    fillers = {
        'uh', 'um', 'erm', 'hmm', 'ah', 'uhh', 'umm', 'like', 'you know', 'sort of', 'kind of'
    }
    # Collapse triple+ duplicate words: "i i i think" -> "i think"
    words = re.split(r"(\s+)", s)
    cleaned = []
    last_word = None
    repeat_count = 0
    for token in words:
        if token.strip() == "":
            cleaned.append(token)
            continue
        w = token.strip()
        wl = w.lower()
        if wl in fillers:
            # skip filler
            continue
        if last_word is not None and wl == last_word:
            repeat_count += 1
            if repeat_count >= 2:
                # allow at most 2 consecutive duplicates
                continue
        else:
            repeat_count = 0
        cleaned.append(w)
        last_word = wl
    s = "".join(cleaned)
    # Collapse elongated letters: soooo -> soo; uhhhh -> uh
    s = re.sub(r"([a-zA-Z])\1{2,}", r"\1\1", s)
    # Remove stray single characters repeated with spaces: "a a a" -> "a"
    s = re.sub(r"\b([a-zA-Z])(?:\s+\1){2,}\b", r"\1", s)
    return s.strip()


def _prepare_spoken_text(text: str) -> str:
    """Prepare text for TTS: remove raw URLs and optionally citations.
    - Drops segments like "— https://..."
    - Removes standalone URLs
    - Optionally strips numeric citations like [1], [2] if TTS_SPEAK_CITATIONS=0
    """
    if not text:
        return text
    s = text
    try:
        # Remove em dash followed by URL
        s = re.sub(r"\s—\shttps?://\S+", "", s)
        # Remove parentheses that only contain a URL
        s = re.sub(r"\(\s*https?://[^)]+\)", "", s)
        # Remove raw URLs anywhere
        s = re.sub(r"https?://\S+", "", s)
        # Collapse extra spaces left by removals
        s = re.sub(r"\s{2,}", " ", s).strip()
        # Optionally strip numeric citations [1], [2]
        if os.getenv('TTS_SPEAK_CITATIONS', '0') != '1':
            s = re.sub(r"\s*\[(?:\d+|[a-zA-Z])\]", "", s)
            # Remove trailing "Sources:" sections made of bullets/links
            lines = [ln for ln in s.splitlines() if ln.strip()]
            pruned = []
            skipping = False
            for ln in lines:
                low = ln.lower()
                if not skipping and (low.startswith('sources:') or low.startswith('source:')):
                    skipping = True
                    continue
                if skipping:
                    # Skip lines that look like links or citations
                    if re.search(r"https?://|\[(?:\d+|[a-zA-Z])\]", ln):
                        continue
                    # Stop skipping if normal sentence resumes
                    if len(ln.split()) >= 4 and not re.search(r"https?://", ln):
                        skipping = False
                        pruned.append(ln)
                    continue
                pruned.append(ln)
            s = "\n".join(pruned).strip()
    except Exception:
        pass
    return s


def speak(text: str):
    global CURRENT_TTS_PROC, CURRENT_TTS_TMPFILE
    # Ensure we never send empty strings to TTS
    msg = (text or '').strip() or 'Okay.'
    msg = _strip_emojis(msg)
    use = (os.getenv('TTS_ENGINE', 'say') or 'say').lower()
    # If not explicitly set, default to Kokoro when its server URL is configured
    if (os.getenv('TTS_ENGINE') is None or os.getenv('TTS_ENGINE') == '') and (os.getenv('KOKORO_BASE_URL') or '').strip():
        use = 'kokoro'
    voice = os.getenv('TTS_VOICE', 'Oliver')
    rate_wpm = os.getenv('TTS_RATE_WPM', '200')
    debug = (os.getenv('TTS_DEBUG', '0') == '1')
    if debug:
        print(f"[TTS] engine={use} voice={voice} rate={rate_wpm} text={msg[:80]!r}")

    if use == 'elevenlabs':
        # High-quality online TTS with small retry loop and optional strict mode
        import json as _json
        api_key = os.getenv('ELEVENLABS_API_KEY') or os.getenv('ELEVEN_API_KEY')
        voice_id = os.getenv('ELEVENLABS_VOICE_ID') or os.getenv('ELEVEN_VOICE_ID')
        model_id = os.getenv('ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2')
        strict = (os.getenv('TTS_STRICT', '0') == '1')
        retries = 0
        try:
            retries = int(os.getenv('TTS_RETRIES', '2'))
        except Exception:
            retries = 2
        if not api_key or not voice_id:
            if strict:
                # Always surface a warning so silent failures are visible
                print("[TTS elevenlabs] Missing API key or voice id and strict mode is on; audio suppressed.")
                return
            use = 'say'
        else:
            import requests as _req
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            headers = {
                'xi-api-key': api_key,
                'accept': 'audio/mpeg',
                'content-type': 'application/json',
            }
            payload = {
                'text': msg,
                'model_id': model_id,
                'voice_settings': {
                    'stability': 0.5,
                    'similarity_boost': 0.8,
                    'style': 0.2,
                    'use_speaker_boost': True
                }
            }
            last_err = None
            for attempt in range(retries + 1):
                try:
                    resp = _req.post(url, headers=headers, data=_json.dumps(payload), timeout=30)
                    resp.raise_for_status()
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        tmp = f.name
                        f.write(resp.content)
                    _play_file_async(tmp, display_text=msg)
                    return
                except Exception as e:
                    last_err = e
                    # brief backoff
                    try:
                        time.sleep(0.4 * (attempt + 1))
                    except Exception:
                        pass
            # If we exhausted retries
            if strict:
                print(f"[TTS elevenlabs] failed after retries and strict mode is on: {last_err}")
                return
            if debug:
                print(f"[TTS elevenlabs fallback] {last_err}. Falling back to system TTS.")
            use = (os.getenv('TTS_FALLBACK_ENGINE', 'say') or 'say').lower()
    if use == 'edge':
        # Optional: Edge TTS (neural voices). Requires edge-tts package.
        try:
            import asyncio
            import edge_tts
            edge_voice = os.getenv('TTS_EDGE_VOICE', 'en-GB-DanielNeural')
            edge_rate = os.getenv('TTS_EDGE_RATE', '+0%')
            async def _run():
                communicate = edge_tts.Communicate(msg, voice=edge_voice, rate=edge_rate)
                with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                    out = f.name
                await communicate.save(out)
                _play_file_async(out, display_text=msg)
            asyncio.run(_run())
            return
        except Exception as e:
            if debug:
                print(f"[TTS edge fallback] {e}")
            # fallback to say
            use = 'say'

    if use == 'piper':
        # Local TTS using Piper CLI. Requires a voice model (.onnx + .json) and piper binary.
        # Env:
        #   PIPER_BIN: path to piper binary (default tools/piper/piper/piper)
        #   PIPER_MODEL_PATH: path to voice .onnx
        #   PIPER_CONFIG_PATH: path to voice .onnx.json
        #   PIPER_NOISE_SCALE, PIPER_LENGTH_SCALE (optional numeric strings)
        bin_path = os.getenv('PIPER_BIN', os.path.abspath('tools/piper/piper/piper'))
        model_path = os.getenv('PIPER_MODEL_PATH')
        config_path = os.getenv('PIPER_CONFIG_PATH')
        if not (model_path and config_path and os.path.isfile(bin_path) and os.path.isfile(model_path) and os.path.isfile(config_path)):
            if debug:
                print("[TTS piper] Missing binary or model/config. Falling back.")
            use = (os.getenv('TTS_FALLBACK_ENGINE', 'say') or 'say').lower()
        else:
            try:
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                    wav_out = f.name
                # Build command
                cmd = [bin_path, '-m', model_path, '-c', config_path, '-f', wav_out]
                ns = os.getenv('PIPER_NOISE_SCALE')
                ls = os.getenv('PIPER_LENGTH_SCALE')
                if ns:
                    cmd += ['--noise_scale', ns]
                if ls:
                    cmd += ['--length_scale', ls]
                # Piper reads text from stdin
                proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                try:
                    proc.communicate(input=msg.encode('utf-8'), timeout=60)
                except Exception:
                    proc.kill()
                    raise
                if proc.returncode == 0 and os.path.isfile(wav_out):
                    env, dt = _compute_wav_levels(wav_out)
                    _play_file_async(wav_out, levels=env, display_text=msg, frame_dt=dt)
                    return
                else:
                    if debug:
                        out, err = proc.communicate()
                        print(f"[TTS piper] failed rc={proc.returncode} out={out[:200]} err={err[:200]}")
            except Exception as e:
                if debug:
                    print(f"[TTS piper] error: {e}")
            # fallback
            use = (os.getenv('TTS_FALLBACK_ENGINE', 'say') or 'say').lower()

    if use == 'kokoro':
        # Local HTTP server for Kokoro-ONNX (e.g., HearItServer). Expects POST /synthesize
        # Env:
        #   KOKORO_BASE_URL (e.g., http://127.0.0.1:8000)
        #   KOKORO_VOICE (voice name/id per server)
        #   KOKORO_SPEED (float, 1.0 = normal; >1.0 faster)
        try:
            import requests as _req
            base = os.getenv('KOKORO_BASE_URL') or ''
            voice = os.getenv('KOKORO_VOICE', 'daniel')
            # Friendly aliases: map to available kokoro-onnx styles
            if voice and '/' not in voice:
                alias = voice.strip().lower()
                alias_map = {
                    'daniel': 'am_michael',
                    'ryan': 'am_adam',
                    'amy': 'af_nicole',
                    'michael': 'am_michael',
                }
                voice = alias_map.get(alias, voice)
            try:
                speed = float(os.getenv('KOKORO_SPEED', '1.0'))
            except Exception:
                speed = 1.0
            if base:
                url = base.rstrip('/') + '/synthesize'
                payload = {'text': msg, 'voice': voice, 'speed': speed}
                resp = _req.post(url, json=payload, timeout=30)
                resp.raise_for_status()
                # Expect binary audio (wav or mp3)
                ctype = resp.headers.get('content-type', '')
                ext = '.mp3' if 'mpeg' in ctype or 'mp3' in ctype else '.wav'
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                    out = f.name
                    f.write(resp.content)
                env = None
                dt = 0.03
                if ext == '.wav':
                    try:
                        env, dt = _compute_wav_levels(out)
                    except Exception:
                        env = None
                _play_file_async(out, levels=env, display_text=msg, frame_dt=dt)
                return
        except Exception as e:
            if debug:
                print(f"[TTS kokoro fallback] {e}")
        use = (os.getenv('TTS_FALLBACK_ENGINE', 'say') or 'say').lower()

    if use == 'marytts':
        # Local MaryTTS server (Java). Default http://localhost:59125/process
        # Env:
        #   MARYTTS_BASE_URL, MARYTTS_VOICE (e.g., dfki-pavoque-neutral)
        try:
            import requests as _req
            base = os.getenv('MARYTTS_BASE_URL', 'http://127.0.0.1:59125')
            voice = os.getenv('MARYTTS_VOICE', 'dfki-pavoque-neutral')
            url = base.rstrip('/') + '/process'
            params = {
                'INPUT_TEXT': msg,
                'INPUT_TYPE': 'TEXT',
                'OUTPUT_TYPE': 'AUDIO',
                'AUDIO': 'WAVE_FILE',
                'LOCALE': 'en_US',
                'VOICE': voice,
            }
            resp = _req.get(url, params=params, timeout=30)
            resp.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as f:
                out = f.name
                f.write(resp.content)
            env, dt = _compute_wav_levels(out)
            _play_file_async(out, levels=env, display_text=msg, frame_dt=dt)
            return
        except Exception as e:
            if debug:
                print(f"[TTS marytts fallback] {e}")
        use = (os.getenv('TTS_FALLBACK_ENGINE', 'say') or 'say').lower()

    if use == 'say':
        try:
            # Prefer macOS say for reliability and naturalness
            # macOS voices to try in order if preferred not available
            preferred = [voice, 'Daniel', 'Alex', 'Oliver']
            said = False
            for v in preferred:
                if not v:
                    continue
                try:
                    # Run asynchronously to allow barge-in
                    stop_speaking()
                    proc = subprocess.Popen(['say', '-v', v, '-r', rate_wpm, msg])
                    with CURRENT_TTS_LOCK:
                        CURRENT_TTS_PROC = proc
                        CURRENT_TTS_TMPFILE = None
                    said = True
                    # Overlay follow for 'say'
                    _overlay_write('speaking', msg, 0.35)
                    def _watch_say(p=proc):
                        try:
                            p.wait()
                        except Exception:
                            pass
                        finally:
                            _overlay_write('idle', '')
                    threading.Thread(target=_watch_say, daemon=True).start()
                    # Do not wait; watcher thread not needed for 'say'
                    break
                except Exception:
                    continue
            if not said:
                stop_speaking()
                try:
                    proc = subprocess.Popen(['say', msg])
                    with CURRENT_TTS_LOCK:
                        CURRENT_TTS_PROC = proc
                        CURRENT_TTS_TMPFILE = None
                    _overlay_write('speaking', msg, 0.35)
                    def _watch_say2(p=proc):
                        try:
                            p.wait()
                        except Exception:
                            pass
                        finally:
                            _overlay_write('idle', '')
                    threading.Thread(target=_watch_say2, daemon=True).start()
                except Exception:
                    pass
            return
        except Exception:
            # Fallback to pyttsx3
            try:
                # Best-effort: pyttsx3 is synchronous; attempt to stop any playing 'say/afplay' first
                if engine is not None:
                    stop_speaking()
                    _overlay_write('speaking', msg, 0.35)
                    engine.say(msg)
                    engine.runAndWait()
                    _overlay_write('idle', '')
                    return
            except Exception:
                # Final fallback: gTTS + afplay
                try:
                    from gtts import gTTS
                    t = gTTS(text=msg, lang='en')
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        tmp = f.name
                    t.save(tmp)
                    _play_file_async(tmp, display_text=msg)
                except Exception:
                    print("[TTS suppressed]", msg)
    else:
        # Prefer pyttsx3 first, fallback to say
        try:
            if engine is not None:
                stop_speaking()
                engine.say(msg)
                engine.runAndWait()
            else:
                raise RuntimeError("pyttsx3 engine unavailable")
        except Exception:
            try:
                stop_speaking()
                proc = subprocess.Popen(['say', '-v', voice, '-r', rate_wpm, msg])
                with CURRENT_TTS_LOCK:
                    CURRENT_TTS_PROC = proc
                    CURRENT_TTS_TMPFILE = None
                _overlay_write('speaking', msg, 0.35)
                def _watch_say3(p=proc):
                    try:
                        p.wait()
                    except Exception:
                        pass
                    finally:
                        _overlay_write('idle', '')
                threading.Thread(target=_watch_say3, daemon=True).start()
            except Exception:
                try:
                    from gtts import gTTS
                    t = gTTS(text=msg, lang='en')
                    with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as f:
                        tmp = f.name
                    t.save(tmp)
                    _play_file_async(tmp, display_text=msg)
                except Exception:
                    print("[TTS suppressed]", msg)

STOP_EVENT = threading.Event()
# Global handle to wake-word audio stream so we can close it on shutdown
AUDIO_STREAM_REF = None


def speak_streaming(chunks_iter):
    """Speak progressively, emitting sentences as they complete using the existing speak() routing."""
    last_spoken = None
    for sent in _yield_sentences_from_stream(chunks_iter):
        if not sent:
            continue
        # De-duplicate identical consecutive sentences
        if last_spoken and sent.strip() == last_spoken:
            continue
        # Wait for current speech to finish before speaking next sentence to avoid overlap/echo
        while is_speaking() and not STOP_EVENT.is_set():
            time.sleep(0.02)
        speak(sent)
        last_spoken = sent.strip()
        time.sleep(0.03)


def main():
    # Lazy import to avoid requiring SpeechRecognition for TTS-only scripts
    import speech_recognition as sr
    from agent.core import ChatSession
    # Ensure overlay is running if enabled
    _maybe_launch_overlay()
    # If wake-word mode is enabled, run a silent background listener. On trigger, speak 'yo',
    # then handle conversation until a stop phrase is spoken, returning to standby afterwards.
    if os.getenv('WAKE_MODE', '0') == '1':
        print("Standby: listening for wake word… (type 'shutdown' + Enter to exit)")
        _maybe_launch_overlay()
        _overlay_write('listening', '')
        start_command_listener()
        try:
            run_wakeword_loop()
        except KeyboardInterrupt:
            print("Exiting wake mode.")
        finally:
            # Emit a clear termination marker for external supervisors/toggles
            try:
                print("Exited", flush=True)
            except Exception:
                pass
            _maybe_quit_overlay()
        return

    # Start command listener to allow keyboard barge-in/stop even outside wake mode
    start_command_listener()

    speak("Ready. Say quit to exit.")

    chat = ChatSession()

    # Initialize microphone listener
    r = sr.Recognizer()
    # Tune recognition for longer prompts and robust VAD (env-overridable)
    r.dynamic_energy_threshold = True
    r.energy_threshold = 300  # starting point; will adapt
    try:
        r.pause_threshold = float(os.getenv('STT_PAUSE_SEC', '1.1'))
    except Exception:
        r.pause_threshold = 1.1
    try:
        r.phrase_threshold = float(os.getenv('STT_PHRASE_SEC', '0.5'))
    except Exception:
        r.phrase_threshold = 0.5
    try:
        r.non_speaking_duration = float(os.getenv('STT_NON_SPEAK_SEC', '0.8'))
    except Exception:
        r.non_speaking_duration = 0.8

    stt_timeout = int(os.getenv('STT_TIMEOUT', '8'))
    stt_max_seconds = int(os.getenv('STT_MAX_SECONDS', '30'))

    with sr.Microphone() as source:
        r.adjust_for_ambient_noise(source, duration=0.5)
        print("Listening... (say 'quit' to exit)")
        _overlay_write('listening', '')
        while True:
            try:
                # If TTS is speaking, wait briefly to avoid self-feedback
                while is_speaking():
                    time.sleep(0.05)
                _overlay_write('listening', '')
                audio = r.listen(source, timeout=stt_timeout, phrase_time_limit=stt_max_seconds)
            except sr.WaitTimeoutError:
                continue
            try:
                text = r.recognize_google(audio)
                clean = _clean_transcript(text)
                if not clean:
                    continue
                print(f"You: {clean}")
                if clean.lower().strip() in {"quit", "exit", "stop"}:
                    stop_speaking()
                    speak("Goodbye")
                    _maybe_quit_overlay()
                    break
                try:
                    if os.getenv('LLM_STREAM', '1') == '1' and hasattr(chat, 'ask_stream'):
                        # Speak progressively while the model is generating
                        _overlay_write('thinking', clean)
                        gen = chat.ask_stream(clean)
                        speak_streaming(gen)
                        # After streaming completes, print the final assistant message from history
                        last = chat.history[-1]["content"] if chat.history and chat.history[-1]["role"] == "assistant" else ""
                        if last:
                            print(f"Assistant: {last}")
                        # Already spoken progressively
                        to_say = None
                    else:
                        _overlay_write('thinking', clean)
                        reply = chat.ask(clean)
                        print(f"Assistant: {reply}")
                        to_say = _prepare_spoken_text(reply)
                except Exception as e:
                    reply = f"Error: {e}"
                    print(f"Assistant: {reply}")
                    to_say = _prepare_spoken_text(reply)
                if to_say:
                    _speak_maybe_chunked(to_say)
                # Small cooldown after speaking before listening resumes to avoid capturing tail audio
                time.sleep(0.05)
                _overlay_write('listening', '')
            except sr.UnknownValueError:
                # Be quiet on small ASR misses to keep latency low
                print("(didn't catch that)")
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")


# Note: program entry point moved to end of file after all function definitions


def run_wakeword_loop():
    """Listen continuously with Porcupine and say 'yo' when the wake word is detected.
    Uses env:
      - PICOVOICE_ACCESS_KEY: required Porcupine access key
      - WAKEWORD_KEYWORD: preferred keyword (default 'jarvis'); attempts 'hey jarvis' then falls back
    """
    try:
        import pvporcupine
        import pyaudio
        import struct
    except Exception as e:
        print(f"Wake word dependencies missing: {e}\nInstall 'pvporcupine' and 'pyaudio' in your venv.")
        return

    access_key = os.getenv('PICOVOICE_ACCESS_KEY')
    if not access_key or access_key.strip().lower() in {"your_key_here", "<your_key_here>"}:
        print("PICOVOICE_ACCESS_KEY is missing or placeholder. Set it in your .env to enable wake word mode.")
        return

    keyword_pref = (os.getenv('WAKEWORD_KEYWORD') or 'jarvis').lower()
    keyword_path = os.getenv('WAKEWORD_KEYWORD_PATH')  # optional custom .ppn path
    try:
        sensitivity = float(os.getenv('WAKEWORD_SENSITIVITY', '0.6'))
    except Exception:
        sensitivity = 0.6
    porcupine = None
    pa = None
    audio_stream = None
    try:
        used_kw = keyword_pref
        if keyword_path and os.path.isfile(keyword_path):
            print(f"[wake] Using custom keyword file: {keyword_path} (sensitivity={sensitivity})")
            porcupine = pvporcupine.create(
                access_key=access_key,
                keyword_paths=[keyword_path],
                sensitivities=[sensitivity],
            )
            used_kw = os.path.basename(keyword_path)
        else:
            # Try preferred built-in keyword first; 'hey jarvis' may not be built-in.
            try:
                porcupine = pvporcupine.create(access_key=access_key, keywords=[keyword_pref], sensitivities=[sensitivity])
            except ValueError as ve:
                print(f"[wake] Built-in keyword '{keyword_pref}' not available. Falling back to 'jarvis'. ({ve})")
                used_kw = 'jarvis'
                porcupine = pvporcupine.create(access_key=access_key, keywords=[used_kw], sensitivities=[sensitivity])
            except Exception as e:
                print(f"[wake] Failed to use keyword '{keyword_pref}', falling back to 'jarvis' ({e})")
                used_kw = 'jarvis'
                porcupine = pvporcupine.create(access_key=access_key, keywords=[used_kw], sensitivities=[sensitivity])

        pa = pyaudio.PyAudio()
        # Optional specific input device index
        try:
            dev_idx = os.getenv('WAKE_INPUT_DEVICE_INDEX')
            dev_idx = int(dev_idx) if dev_idx is not None and dev_idx != '' else None
        except Exception:
            dev_idx = None
        def _open_stream():
            return pa.open(
                rate=porcupine.sample_rate,
                channels=1,
                format=pyaudio.paInt16,
                input=True,
                input_device_index=dev_idx,
                frames_per_buffer=porcupine.frame_length,
            )
        audio_stream = _open_stream()
        # Expose stream for command listener to close on shutdown
        global AUDIO_STREAM_REF
        AUDIO_STREAM_REF = audio_stream

        print(f"✅ Wake word standby: listening for '{used_kw}'.")
        # Lazy import to avoid mandatory dependency for TTS-only runs
        try:
            from agent.core import ChatSession
        except Exception:
            ChatSession = None  # type: ignore
        chat = ChatSession() if ChatSession else None
        cooldown_until = 0.0
        while not STOP_EVENT.is_set():
            # If the stream was stopped/closed (e.g., by shutdown command), exit immediately
            try:
                if not audio_stream.is_active():
                    # Try to reopen stream unless shutting down
                    if STOP_EVENT.is_set():
                        break
                    try:
                        audio_stream = _open_stream()
                        AUDIO_STREAM_REF = audio_stream
                        cooldown_until = time.time() + 0.2
                        continue
                    except Exception:
                        time.sleep(0.1)
                        continue
            except Exception:
                if STOP_EVENT.is_set():
                    break
                # Attempt reopen on exception
                try:
                    audio_stream = _open_stream()
                    AUDIO_STREAM_REF = audio_stream
                    cooldown_until = time.time() + 0.2
                    continue
                except Exception:
                    time.sleep(0.1)
                    continue
            try:
                pcm = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            except Exception:
                # On read error, exit if we're shutting down; otherwise continue
                if STOP_EVENT.is_set():
                    break
                else:
                    continue
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)
            idx = porcupine.process(pcm)
            now = time.time()
            if idx >= 0 and now >= cooldown_until:
                # Triggered
                # Make overlay visible and give quick feedback
                _overlay_write('speaking', 'yo', 0.6, visible=True)
                speak("yo")
                # Debounce for a short period to avoid multiple triggers on one utterance
                cooldown_until = now + 1.0
                # Enter active interaction until stop phrase, then return to standby
                try:
                    # Pause and release wake listening stream to free mic for STT
                    try:
                        if audio_stream is not None:
                            try:
                                if audio_stream.is_active():
                                    audio_stream.stop_stream()
                            except Exception:
                                pass
                            try:
                                audio_stream.close()
                            except Exception:
                                pass
                            audio_stream = None
                            AUDIO_STREAM_REF = None
                    except Exception:
                        pass
                    if chat is None:
                        print("[wake] Chat session unavailable (missing dependencies).")
                    else:
                        active_interaction(chat)
                except Exception as e:
                    print(f"[wake->active] error: {e}")
                # Resume wake listening if not shutting down
                if STOP_EVENT.is_set():
                    break
                try:
                    # Fully reset PyAudio to avoid AUHAL -50 after closing
                    try:
                        if pa is not None:
                            pa.terminate()
                    except Exception:
                        pass
                    import pyaudio as _p
                    pa = _p.PyAudio()
                    audio_stream = _open_stream()
                    AUDIO_STREAM_REF = audio_stream
                    # Small cooldown before listening resumes
                    cooldown_until = time.time() + 0.3
                    print("Standby: listening for wake word… (type 'shutdown' + Enter to exit)")
                    print(f"✅ Wake word standby: listening for '{used_kw}'.")
                    # Hide overlay until next activation
                    _overlay_write('idle', '', 0.0, visible=False)
                except Exception as e:
                    print(f"[wake] failed to resume mic: {e}")
        print("Shutting down standby loop.")
        try:
            speak("Shutting down. Goodbye.")
        except Exception:
            pass
        # Print termination marker as soon as the loop ends
        try:
            print("Exited", flush=True)
        except Exception:
            pass
    except KeyboardInterrupt:
        print("Keyboard interrupt: exiting wake mode.")
    finally:
        if audio_stream:
            try:
                audio_stream.close()
            except Exception:
                pass
        if pa:
            try:
                pa.terminate()
            except Exception:
                pass
        if porcupine:
            try:
                porcupine.delete()
            except Exception:
                pass


def active_interaction(chat):
    """Run the normal STT -> LLM -> TTS flow until a stop phrase is spoken, then return.
    Keeps the session memory in the provided ChatSession.
    """
    import speech_recognition as sr
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True
    r.energy_threshold = 300
    try:
        r.pause_threshold = float(os.getenv('STT_PAUSE_SEC', '1.1'))
    except Exception:
        r.pause_threshold = 1.1
    try:
        r.phrase_threshold = float(os.getenv('STT_PHRASE_SEC', '0.5'))
    except Exception:
        r.phrase_threshold = 0.5
    try:
        r.non_speaking_duration = float(os.getenv('STT_NON_SPEAK_SEC', '0.8'))
    except Exception:
        r.non_speaking_duration = 0.8

    stt_timeout = int(os.getenv('STT_TIMEOUT', '8'))
    stt_max_seconds = int(os.getenv('STT_MAX_SECONDS', '30'))

    stop_phrases = {
        "exit", "quit", "stop", "that's all for now", "thats all for now", "stop listening", "go to sleep", "sleep", "standby"
    }

    with sr.Microphone() as source:
        # Briefly calibrate noise floor
        r.adjust_for_ambient_noise(source, duration=0.2)
        speak("I'm listening.")
        _overlay_write('listening', '')
        while not STOP_EVENT.is_set():
            try:
                while is_speaking():
                    time.sleep(0.05)
                _overlay_write('listening', '')
                audio = r.listen(source, timeout=stt_timeout, phrase_time_limit=stt_max_seconds)
            except sr.WaitTimeoutError:
                if STOP_EVENT.is_set():
                    break
                continue
            try:
                # Exit immediately if shutdown was typed during capture
                if STOP_EVENT.is_set():
                    break
                text = r.recognize_google(audio)
                clean = _clean_transcript(text)
                if not clean:
                    continue
                print(f"You: {clean}")
                low = clean.lower().strip()
                if low in stop_phrases:
                    stop_speaking()
                    speak("Back to standby.")
                    return
                # Normal ask/answer
                try:
                    # Stream while generating if enabled
                    if os.getenv('LLM_STREAM', '1') == '1' and hasattr(chat, 'ask_stream'):
                        # Progressive speech: speak sentences as they form
                        _overlay_write('thinking', clean)
                        gen = chat.ask_stream(clean)
                        speak_streaming(gen)
                        # ChatSession updates history internally; print the last assistant message for console visibility
                        last = chat.history[-1]["content"] if chat.history and chat.history[-1]["role"] == "assistant" else ""
                        if last:
                            print(f"Assistant: {last}")
                        to_say = None  # already spoken
                    else:
                        _overlay_write('thinking', clean)
                        reply = chat.ask(clean)
                        print(f"Assistant: {reply}")
                        to_say = _prepare_spoken_text(reply)
                except Exception as e:
                    err = f"Error: {e}"
                    print(f"Assistant: {err}")
                    to_say = _prepare_spoken_text(err)
                if to_say:
                    _speak_maybe_chunked(to_say)
                time.sleep(0.05)
                _overlay_write('listening', '')
            except sr.UnknownValueError:
                print("(didn't catch that)")
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")
        # Exit voice loop quickly on shutdown
        if STOP_EVENT.is_set():
            return


def start_command_listener():
    """Start a daemon thread that listens for terminal commands to stop the program.
    Type 'shutdown', 'exit', or 'quit' and press Enter to terminate wake mode.
    """
    def _worker():
        try:
            while not STOP_EVENT.is_set():
                try:
                    line = input()
                except EOFError:
                    break
                if not line:
                    continue
                cmd = line.strip().lower()
                if cmd in {"shutdown", "exit", "quit"}:
                    print("Received shutdown command. Exiting…")
                    STOP_EVENT.set()
                    # Stop any ongoing speech immediately
                    try:
                        stop_speaking()
                    except Exception:
                        pass
                    # Close wake audio stream to unblock read immediately
                    try:
                        global AUDIO_STREAM_REF
                        if AUDIO_STREAM_REF is not None:
                            try:
                                if AUDIO_STREAM_REF.is_active():
                                    AUDIO_STREAM_REF.stop_stream()
                            except Exception:
                                pass
                            try:
                                AUDIO_STREAM_REF.close()
                            except Exception:
                                pass
                            AUDIO_STREAM_REF = None
                    except Exception:
                        pass
                    # Timed hard-exit fallback to guarantee shutdown even if blocked in I/O
                    try:
                        import threading as _th
                        import time as _t
                        import os as _os
                        timeout_s = 5.0
                        try:
                            timeout_s = float(os.getenv('GRACEFUL_TIMEOUT_SECONDS', '5'))
                        except Exception:
                            pass
                        def _kill_later():
                            _t.sleep(timeout_s)
                            # Emit marker before hard exit for external toggles
                            try:
                                print("Exited", flush=True)
                            except Exception:
                                pass
                            try:
                                _maybe_quit_overlay()
                            except Exception:
                                pass
                            _os._exit(0)
                        _th.Thread(target=_kill_later, daemon=True).start()
                    except Exception:
                        pass
                    break
                # Barge-in stop: stop speaking without exiting process
                if cmd in {"stop", "stahp"}:
                    try:
                        stop_speaking()
                        print("(stopped speaking)")
                    except Exception:
                        pass
        except Exception as e:
            print(f"[command-listener] error: {e}")

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


if __name__ == "__main__":
    main()
