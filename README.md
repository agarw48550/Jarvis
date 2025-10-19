## JarvisAI (local voice assistant, local/cloud LLM)

JarvisAI is a Mac-first voice assistant with:
- Wake word standby and fast barge-in (type `stop` to cut speech; `shutdown` exits)
- Local STT and clean TTS with multiple engines (Kokoro, macOS say, ElevenLabs, Piper, MaryTTS)
- Tool-first routing for macOS Music, Battery, Timers/Stopwatch, Shortcuts, Time/Location
- Grounded web answers with concise, single-source citations
- Personality and lightweight memory (add/search/clear)

It works with OpenAI-compatible LLMs (LM Studio locally or any compatible cloud provider).

---

## Project timeline and evolution

This timeline documents how JarvisAI grew from a simple voice loop into a fast, local-first assistant with rich tools.

- Phase 1 — Stabilization and UX hardening
  - Added wake standby and graceful shutdown marker (type "shutdown" to exit cleanly)
  - Implemented self-hearing mitigation: pause STT while speaking, plus a short cooldown
  - Lazy imports for faster cold starts; sentence-chunked speaking; barge-in via "stop"
  - Repo hygiene and secrets scrub (.gitignore, .env.example)

- Phase 2 — Local TTS migration (Kokoro)
  - Replaced cloud TTS with a local Kokoro server (FastAPI + kokoro-onnx)
  - Added /health and /synthesize endpoints; voice aliasing; speed control
  - Helper scripts to start and test the TTS server

- Phase 3 — Environment recovery
  - Reintroduced a runnable .env.local; prefer external paths for env files for safety
  - Sanitized wakeword keys and other secrets

- Phase 4 — Kokoro bring-up
  - Created a 3.12 venv specifically for Kokoro server deps
  - Downloaded proper kokoro-v1.0.onnx and voices.bin; started server and verified audio

- Phase 5 — Latency and quality
  - Removed double time-stretching to eliminate metallic echo; use native Kokoro speed
  - Implemented LLM SSE streaming with progressive TTS (speak while generating)

- Phase 6 — Echo residuals
  - Eliminated overlap by gating playback: wait for current sentence to finish before the next
  - Added sentence de-duplication and tiny inter-chunk gaps to avoid clicks

- Phase 7 — Cleanup and repo sync
  - Removed stray audio artifacts; tightened .gitignore; cleaned README leftovers
  - Staged, committed, and pushed changes to main

- Phase 8 — Feature enrichment (browser, search, weather)
  - Added browser helpers (YouTube/GitHub/Instagram, trending, YouTube search)
  - Implemented a keyless weather report using Open‑Meteo; wired into the tool router and direct phrases

- Phase 9 — macOS system controls
  - Added open/quit app, close window, fullscreen toggle, and volume controls via AppleScript/open
  - Added direct phrase triggers for snappy control (e.g., "open Safari", "mute")

- Phase 10 — Features inspired by community assistants
  - Calculator (safe AST), Wikipedia summaries/search, news headlines via RSS, and fun utilities (joke/coin/dice)
  - Open arbitrary website or search query in the browser

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

## Features and capabilities

Core experience
- Wake word mode with Porcupine; classic interactive mode without wake
- Progressive speech while the LLM is still generating (low perceived latency)
- Barge-in: type "stop" to immediately cut speech; type "shutdown" to exit
- Persona support via personality.yaml for tone/humor/formality/terseness (optional)

Speech (TTS)
- Engines: Kokoro (local, neural), macOS say (local), ElevenLabs, Piper, MaryTTS
- Streaming sentence-by-sentence speaking; overlap prevention and click-free boundaries
- Kokoro voice aliasing and speed control; optional macOS voice selection

Hearing (STT)
- SpeechRecognition + PyAudio; pause STT while speaking to avoid self-hear loops
- Tunable pause/phrase/non-speak windows to reduce truncation

LLM integration
- OpenAI-compatible client; works with LM Studio locally or cloud providers
- Normal chat and SSE streaming; concise, sanitized replies (no chain-of-thought leakage)

Grounded web answers
- DuckDuckGo HTML search; fetch and relevance slice of top source(s)
- Short, direct answer with a single bracket citation like [1]
- Optional source listing printed to console; TTS omits URLs/citations by default

macOS tools and automations
- Music control: play/pause/toggle/next/previous
- Battery: quick status via pmset
- Timers + Stopwatch: in-process, with status/cancel; stopwatch start/stop/reset
- Shortcuts: run by name; alias phrases via SHORTCUTS_ALIASES
- System controls: open/quit app, close window, toggle fullscreen, volume up/down, mute/unmute

Browser and web helpers
- Open YouTube/GitHub/Instagram, YouTube Trending
- YouTube search for a topic
- Open arbitrary website or treat text as a search query

Utilities
- Calculator: safe arithmetic with + - * / // % ** and constants pi, e
- Wikipedia: concise summary and quick search results
- Weather: current conditions via Open‑Meteo (no API key)
- News: top headlines from default RSS feeds or custom NEWS_FEEDS
- Fun: jokes, coin flip, dice roll (supports d20 style)

Memory
- Add/search/clear lightweight in-process notes for quick recall

Direct phrase triggers (examples)
- "open Safari", "quit Spotify", "close window", "fullscreen", "mute", "volume down"
- "open youtube", "youtube trending", "search youtube for lo-fi"
- "open website reddit.com", "open wikipedia.org"
- "calculate 2+2*3", "who is Ada Lovelace", "news", "tell me a joke", "roll d20"
- "set a timer for 2 minutes", "start stopwatch", "run shortcut 'Open Notes'"

Configuration
- .env.example documents all key envs; supports external .env path via JARVIS_DOTENV_PATH/DOTENV_PATH
- Optional KOKORO_SPEED tuning (e.g., 1.05–1.2) for natural pace vs. latency

Privacy & local-first
- Prefers local LLM and local TTS; secrets kept out of repo; external APIs kept minimal and keyless where possible

## Privacy/Security
- Keep `.env`, `credentials.json`, `token.json` private (already ignored in `.gitignore`).
- SmartLife control runs over your local network.

---

## License
MIT

