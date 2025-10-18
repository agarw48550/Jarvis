## JarvisAI (local voice assistant, local/cloud LLM)

JarvisAI is a Mac-first voice assistant with:
- Wake word standby and fast barge-in (type `stop` to cut speech; `shutdown` exits)
- Local STT and clean TTS with multiple engines (Kokoro, macOS say, ElevenLabs, Piper, MaryTTS)
- Tool-first routing for macOS Music, Battery, Timers/Stopwatch, Shortcuts, Time/Location
- Grounded web answers with concise, single-source citations
- Personality and lightweight memory (add/search/clear)

It works with OpenAI-compatible LLMs (LM Studio locally or any compatible cloud provider).

---

## Setup

You’ll typically use two Python environments:
- App venv (runs JarvisAI): Python 3.10+ recommended
- Kokoro venv (optional, only if you want local neural TTS): Python 3.12 recommended

### 1) App venv
```
python3 -m venv jarvisai-venv
source jarvisai-venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set at least:
- LLM endpoint/model (e.g., LM Studio):
  - `LLM_BASE_URL=http://127.0.0.1:1234`
  - `LLM_MODEL=<model_id>`
- TTS (quickest is macOS say):
  - `TTS_ENGINE=say`
  - `TTS_VOICE=Daniel` (or Alex/Oliver)
 

### 2) Kokoro TTS (optional but recommended for natural voice)
Run Kokoro as a local HTTP server in its own venv and point Jarvis to it.

```
python3 -m venv jarvisai-kokoro-venv
source jarvisai-kokoro-venv/bin/activate
pip install fastapi uvicorn soundfile numpy onnxruntime kokoro-onnx

# Place models (not tracked in git):
#  - tools/kokoro/models/kokoro-v1.0.onnx
#  - tools/kokoro/voices/voices.bin and voices.json

uvicorn tools.kokoro.app:app --host 127.0.0.1 --port 8000
```

In your app `.env`:
```
TTS_ENGINE=kokoro
KOKORO_BASE_URL=http://127.0.0.1:8000
KOKORO_VOICE=daniel    # maps to a male voice (am_michael)
KOKORO_SPEED=1.15      # 1.0 = normal; slightly faster
```

Tip: Jarvis auto-defaults to Kokoro if `KOKORO_BASE_URL` is set and `TTS_ENGINE` isn’t.

---

## Run

### Wake word mode
```
source jarvisai-venv/bin/activate
python -c "import os; os.environ.setdefault('WAKE_MODE','1'); import jarvis; jarvis.main()"
```
You should see standby messages. Say your wake word (default ‘jarvis’). Type `shutdown` to exit. Type `stop` to cut speech mid-utterance.

### Classic interactive mode
```
source jarvisai-venv/bin/activate
python jarvis.py
```

Try:
- “What time is it?” (local time tool)
- “Run shortcut ‘Work and Basic’.” (Shortcuts)
- “Set a timer for 2 minutes.” (Timer start)
- “Pause music, then next.” (Music control)
- “Remember my Wi‑Fi is Ayaan-5G; recall Wi‑Fi.” (Memory add/recall)
- “Who is the current president of Singapore?” (Grounded web answer)

TTS quick test (no STT/wake):
```
python scripts/tts_check.py "This is a quick TTS test."
```

---

## Configuration tips

### Speech & barge-in
- `SPEAK_CHUNKED=1` for snappier sentence-by-sentence speaking.
- Type `stop` anytime to barge-in (cuts audio immediately).

### STT tuning (avoid early cut-offs)
- `STT_PAUSE_SEC=1.1`
- `STT_PHRASE_SEC=0.5`
- `STT_NON_SPEAK_SEC=0.8`

### Grounded answers (concise, single source)
- `WEB_SOURCES=1` (default) uses one source for speed and clarity.
- `PRINT_SOURCES=1` prints a sources block with URLs to the console.
- `TTS_SPEAK_CITATIONS=0` ensures TTS doesn’t read “[1]”.

### macOS tools
- Music: play/pause/toggle/next/previous
- Battery: `pmset -g batt` parsing
- Timers & Stopwatch: in-process (with audible completion)
- Shortcuts:
  - Say: `run shortcut "Work and Basic"`
  - Or map aliases: `SHORTCUTS_ALIASES=focus mode:Work and Basic; open notes:Open Notes`

---

## Troubleshooting
- TTS sounds robotic: confirm Kokoro env vars and server; set `TTS_ENGINE=kokoro`, `KOKORO_VOICE=daniel`.
- Assistant hears itself: we pause STT while speaking and add a short cooldown; if needed, lower mic gain or move speakers farther from the mic.
- LM Studio offline: you’ll hear “LM Studio server is offline.” Start LM Studio and pick a model; update `LLM_MODEL`.
- Piper on Apple Silicon: prefer Kokoro (Piper binaries can have arch/dylib issues).

---

## Privacy/Security
- Keep `.env`, `credentials.json`, `token.json` private (already ignored in `.gitignore`).
- SmartLife control runs over your local network.

---

## License
MIT

