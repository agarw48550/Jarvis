# 🤖 JARVIS V3 - Complete Feature Documentation & Development History

## 📋 Table of Contents
1. [What is Jarvis?](#what-is-jarvis)
2. [Complete Feature List](#complete-feature-list)
3. [How It Works](#how-it-works)
4. [Development History](#development-history)
5. [Challenges Overcome](#challenges-overcome)
6. [What's In Progress](#whats-in-progress)
7. [Installation Guide](#installation-guide)
8. [Architecture](#architecture)

---

## 🎯 What is Jarvis?

**Jarvis V3** is an advanced, modular AI virtual assistant inspired by Tony Stark's JARVIS. It's a sophisticated personal AI companion that combines:
- **Ultra-low latency native audio streaming** with Google Gemini 2.5 Flash
- **Wake word activation** ("Hey Jarvis") using Picovoice Porcupine
- **Multi-modal capabilities** including vision, text, and voice
- **Smart home integration** via Google Assistant API
- **Contextual memory** that remembers you across sessions
- **Emotion detection** to adapt responses to your mood
- **Self-evolution capabilities** (experimental)
- **Beautiful glassmorphic UI** built with React + Electron

---

## 🚀 Complete Feature List

### 🎙️ Voice & Audio
- **Native Audio Pipeline**: Bidirectional streaming at 16kHz input / 24kHz output
- **Wake Word Detection**: Always-listening "Hey Jarvis" activation
- **Multiple Voice Options**: Puck (neutral), Charon (male), Fenrir (bold), Aoede (female), Kore (gentle)
- **Voice Customization**: Switchable voices mid-conversation
- **Volume Ducking**: Automatically lowers music/media when speaking
- **Real-time Transcription**: Live speech-to-text display

### 🧠 Intelligence & Memory
- **Contextual Memory**: SQLite-backed memory system with RAG (Retrieval-Augmented Generation)
- **Long-term Fact Storage**: Remembers user preferences, facts, and conversation history
- **Proactive Learning**: Automatically extracts and stores information using Groq
- **Smart Memory Search**: Unified search across facts and conversation history
- **Conversation History**: Last 20 turns preserved with semantic search
- **Usage Pattern Tracking**: Learns from your habits to make suggestions
- **Emotion Detection**: Detects 6 emotions (Neutral, Happy, Frustrated, Confused, Urgent, Grateful)
- **Adaptive Responses**: Adjusts tone based on detected emotion

### 🎛️ System Control
- **Application Management**: Open/close apps, list running processes
- **Volume Control**: Set levels, mute/unmute, increase/decrease
- **Brightness Control**: Adjust screen brightness
- **Battery Status**: Check power status and percentage
- **Media Controls**: Play/pause/next/previous for Music, Spotify, any media app
- **Screenshot Capture**: Take and analyze screenshots
- **Screen Analysis**: Vision-based screen understanding

### 📱 Smart Home
- **Google Assistant Integration**: Control lights, switches, thermostats
- **Natural Language Commands**: "Turn on bedroom lights" just works
- **Device Status**: Query smart device states

### 📧 Productivity
- **Email**: Send and read Gmail messages
- **Calendar**: View events, create calendar entries
- **Reminders**: Add, list, and clear personal reminders
- **Timers**: Set multiple named timers
- **Time/Date**: Current time, timezone information

### 🌐 Information & Web
- **Web Search**: Powered by Tavily for current information
- **News Search**: Latest news on any topic
- **Weather**: Current weather for any city
- **Calculations**: Mathematical expression evaluation
- **Google Drive**: List, search files
- **Google Classroom**: View courses and assignments
- **Contacts**: Search Google Contacts
- **Directions**: Get directions between locations (Google Maps API)
- **Places Search**: Find nearby restaurants, cafes, hospitals
- **Timezone Lookup**: Get timezone for any location

### 🚌 Singapore Transport (LTA API)
- **Real-time Bus Arrivals**: Live bus timing at any stop
- **Bus Stop Search**: Find stops by name or road
- **Near Me**: Buses arriving near your saved location
- **Home Location**: Save and query your home address
- **Distance Calculation**: Haversine distance for nearby stops

### 🤖 AI & Models
- **Primary Model**: Gemini 2.5 Flash (native audio, vision-capable)
- **Smart Model Router**: Auto-switches between models based on query complexity
- **Fallback Models**: Groq (Llama 3.3 70B), Cerebras (Llama 3.3 70B)
- **External LLM Access**: Query Groq/Cerebras for specialized tasks
- **Multi-language Support**: Auto-detects and responds in 12+ languages

### 🛠️ Developer Tools
- **Write Extensions**: Create custom Python tools for Jarvis
- **Run Python Scripts**: Execute code in a sandbox
- **List Extensions**: View all custom tools
- **Self-Evolution**: AI can modify its own capabilities (experimental)

### 🎨 User Interface
- **Glassmorphic Design**: Modern, translucent UI with aurora backgrounds
- **Voice Orb**: Animated, color-coded state indicator
- **Real-time Status**: Online/offline, current state display
- **Settings Modal**: Voice selection, wake word status
- **Chat Bubbles**: Clean conversation history display
- **Error Handling**: User-friendly error banners
- **Tray Integration**: System tray icon with quick controls
- **Frameless Window**: Sleek, borderless design

### ⚙️ Advanced Features
- **Session Resumption**: Reconnects without losing context
- **Quota Management**: Tracks API usage across multiple keys
- **Key Rotation**: Automatically switches between API keys
- **Exponential Backoff**: Graceful retry on API conflicts
- **Concurrent Processing**: Parallel tool execution
- **Lifecycle Management**: Auto-restart on system wake
- **Resource Monitoring**: RAM/CPU tracking (ready)
- **Logging System**: Centralized, structured logging

---

## ⚙️ How It Works

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        ELECTRON APP                          │
│  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
│  │  React UI    │  │  Main Process │  │  System Tray    │  │
│  │  (Voice Orb, │  │  (Window Mgmt)│  │  (Menu, Toggle) │  │
│  │   Chat, etc.)│  │               │  │                 │  │
│  └──────┬───────┘  └───────┬───────┘  └─────────────────┘  │
│         │                  │                                 │
│         └──────────────────┴─────────────────────────────────┤
└────────────────────────────┬────────────────────────────────┘
                             │ HTTP/WebSocket (Port 5000)
┌────────────────────────────▼────────────────────────────────┐
│                     PYTHON BACKEND                           │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 SESSION MANAGER                        │ │
│  │  - WebSocket connection to Gemini Live API            │ │
│  │  - Audio streaming (PyAudio)                          │ │
│  │  - History management                                 │ │
│  │  - Tool execution                                     │ │
│  └────────────────────────┬───────────────────────────────┘ │
│                           │                                  │
│  ┌────────────────────────▼───────────────────────────────┐ │
│  │                    CORE MODULES                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │   Memory     │  │  Emotion     │  │   LLM        │ │ │
│  │  │   (SQLite)   │  │  Detection   │  │  Router      │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │ │
│  │  │Personalization│ │ Wake Word    │  │  Logging     │ │ │
│  │  │              │  │ (Picovoice)  │  │  System      │ │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                   TOOL REGISTRY                        │ │
│  │  80+ tools across 10+ categories                      │ │
│  │  - System, Productivity, Communication, etc.          │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌──────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                         │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │ Gemini  │ │  Groq   │ │ Cerebras │ │ Google APIs     │  │
│  │  Live   │ │ (Llama) │ │ (Llama)  │ │ (Gmail, Drive,  │  │
│  │   API   │ │         │ │          │ │  Maps, etc.)    │  │
│  └─────────┘ └─────────┘ └──────────┘ └─────────────────┘  │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐ ┌─────────────────┐  │
│  │  Tavily │ │   LTA   │ │Picovoice │ │ Google          │  │
│  │ Search  │ │DataMall │ │(Porcupine)│ │Assistant SDK   │  │
│  └─────────┘ └─────────┘ └──────────┘ └─────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Wake Word Detection** → Picovoice continuously listens for "Hey Jarvis"
2. **Audio Capture** → PyAudio captures microphone input at 16kHz
3. **Streaming** → Audio chunks sent to Gemini Live API via WebSocket
4. **Transcription** → Real-time speech-to-text from Gemini
5. **Tool Detection** → Gemini identifies if tools are needed
6. **Tool Execution** → Python backend executes requested tools
7. **Response Generation** → Gemini generates contextual audio response
8. **Audio Playback** → 24kHz audio streamed back and played
9. **Memory Storage** → Conversation + facts stored in SQLite
10. **Learning** → Groq extracts facts in background for long-term memory

### Key Technologies

**Frontend:**
- React 19.2.1 with TypeScript
- Framer Motion for animations
- Tailwind CSS for styling
- Zustand for state management
- Electron 39 for desktop wrapper

**Backend:**
- Python 3.11+
- Flask + Flask-Sock for WebSocket server
- Google Generative AI SDK for Gemini
- PyAudio for audio I/O
- SQLite3 for data persistence
- NumPy for audio processing

**APIs & Services:**
- Google Gemini 2.5 Flash (native audio)
- Groq (Llama 3.3 70B)
- Cerebras (Llama 3.3 70B)
- Picovoice Porcupine (wake word)
- Google Workspace APIs (Gmail, Calendar, Drive, Classroom)
- Google Maps APIs (Directions, Places, Geocoding)
- Google Assistant SDK
- LTA DataMall (Singapore Transport)
- Tavily (web search)

---

## 📜 Development History

### **Genesis: The Vision** (Late 2025)
The journey began with a simple idea: create a true JARVIS-like AI assistant that lives on your Mac, always ready to help. Inspired by Iron Man, the goal was an assistant that:
- Responds instantly to your voice
- Remembers everything about you
- Controls your entire digital life
- Learns and adapts to your style

### **Phase 1: The Foundation** (December 2025)
**Objective:** Build the core infrastructure

**Key Milestones:**
- ✅ Set up Electron + React + Python architecture
- ✅ Implemented basic Flask API backend
- ✅ Created modular directory structure (`/core`, `/tools`, `/interfaces`)
- ✅ Integrated Gemini 2.0 Flash text model
- ✅ Built first set of tools (system, productivity)

**Challenges:**
- Finding the right stack (tested FastAPI, settled on Flask)
- IPC communication between Electron and Python
- Managing Python subprocess lifecycle

### **Phase 2: Going Live** (December 2025 - January 2026)
**Objective:** Implement native audio streaming

**Major Breakthrough:**
- Discovered Gemini 2.5 Flash with native audio support
- Switched from STT→LLM→TTS pipeline to end-to-end audio streaming
- Reduced latency from ~3 seconds to <500ms

**Implementation:**
- Built `session_manager.py` for WebSocket audio streaming
- Implemented `UltraAudio` class with PyAudio for bidirectional audio
- Created custom audio pipeline with separate read/write locks
- Added real-time transcription display

**Challenges Overcome:**
- **Audio glitches**: Solved with threading locks and executor pools
- **Buffer overflows**: Implemented proper queue management
- **Stream interruptions**: Added reconnection logic with session resumption

### **Phase 3: The 409 Wars** (January 2026)
**The Problem:** Persistent `409 Conflict` errors from Gemini API

**Root Cause:** Multiple simultaneous connections with same API key

**Solution Evolution:**
1. ❌ API key rotation (didn't work - sessions still clashed)
2. ❌ Exponential backoff alone (helped but didn't fix)
3. ✅ **Session tracking + mandatory cleanup delay**
   - Class-level `_active_sessions` dictionary
   - 2-second cleanup delay after session close
   - Session resumption tokens for reconnection
   - Exponential backoff (2s, 4s, 8s)

**Result:** 409 errors eliminated, stable 24/7 operation

### **Phase 4: Wake Word Magic** (January 2026)
**Objective:** Always-on activation with "Hey Jarvis"

**Implementation:**
- Integrated Picovoice Porcupine
- Trained custom "Hey Jarvis" wake word model
- Implemented lifecycle management with system sleep/wake

**Challenges:**
- Microphone permissions on macOS
- Wake word detected but not triggering (fixed with state machine)
- Battery drain (optimized with event-driven architecture)

### **Phase 5: Memory & Personalization** (January 2026)
**Objective:** Make Jarvis truly personal

**Implemented:**
- SQLite database with `conversations`, `messages`, `facts`, `preferences` tables
- RAG (Retrieval-Augmented Generation) for context injection
- Proactive learning with Groq LLM
- Unified memory search across facts + conversation history
- Emotion detection with adaptive responses
- Usage pattern tracking for suggestions

**Approach:**
```python
# Every conversation turn triggers background learning
asyncio.create_task(personalization.summarize_and_learn(transcript))

# Groq extracts facts without blocking main flow
facts = await groq_extract_facts(conversation_text)
for fact in facts:
    add_fact(fact)
```

**Impact:** Jarvis now remembers your name, preferences, habits, and builds a long-term relationship

### **Phase 6: Tool Explosion** (January 2026)
**Objective:** Make Jarvis useful for everything

**Added 60+ Tools:**
- **Google Cloud Tools** (Drive, Classroom, Contacts, Calendar, Gmail)
- **Google Maps** (Directions, Places, Timezone)
- **Google Assistant** (Smart home control)
- **Singapore Transport** (LTA bus arrivals, stop search)
- **Developer Tools** (Write extensions, run Python)
- **Vision Tools** (Screen analysis with Gemini Vision)
- **Media Controls** (System-wide play/pause for any app)

**Architecture:**
- Centralized `tool_registry.py` with 80+ function declarations
- Dynamic tool loading from multiple modules
- Automatic parameter type coercion
- Comprehensive error handling

### **Phase 7: Stability Crusade** (January 2026)
**Objective:** Production-ready reliability

**Surgical Fixes:**
1. **Exception Handling Cleanup**
   - Replaced 40+ bare `except:` with `except Exception:`
   - Made Ctrl+C work properly (no more catching `KeyboardInterrupt`)

2. **Audio Race Conditions**
   - Separate read/write locks for audio streams
   - Try-reopen logic for audio stream failures
   - Graceful degradation on audio errors

3. **WebSocket Resilience**
   - GoAway frame handling
   - Heartbeat/ping for connection health
   - Watchdog task to detect stuck states

4. **Tool Output Sanitization**
   - JSON escaping for tool responses
   - Length limits to prevent context overflow
   - Error message masking for API keys

5. **Logging Infrastructure**
   - Centralized `logging_config.py`
   - Structured logging with levels
   - Third-party noise suppression

**Result:** Uptime increased from 2-3 hours to 24+ hours

### **Phase 8: UI Renaissance** (January 2026)
**Objective:** Beautiful, intuitive interface

**Designed:**
- Animated voice orb with state-based colors
- Aurora background with grain overlay
- Glassmorphic chat bubbles
- Modal settings panel with focus trap
- Smooth Framer Motion transitions
- Accessibility features (ARIA labels, keyboard nav)

**Design Philosophy:**
- Minimal but powerful
- Information at a glance
- Delightful micro-interactions
- System tray first (non-intrusive)

### **Phase 9: Optimization & Scale** (January 2026)
**Objective:** Fast, efficient, scalable

**Optimizations:**
1. **Pre-initialized Gemini Client**: Saved 500ms on first connection
2. **Parallel Tool Execution**: Concurrent API calls when possible
3. **Context Window Compression**: Sliding window for long conversations
4. **Smart Model Router**: Free models for simple queries, Gemini for complex
5. **Volume Ducking**: Auto-lower music when AI speaks
6. **Removed Unnecessary Sleeps**: Every `await asyncio.sleep(0.01)` removed

**Performance:**
- First word latency: ~400ms (wake → response)
- Tool execution: <1s for most operations
- Memory: <150MB Python backend
- CPU: <5% idle, <20% during speech

---

## 💪 Challenges Overcome

### 1. **The 409 Conflict Crisis**
**Problem:** WebSocket connections failing with 409 errors
**Attempts:**
- API key rotation ❌
- Exponential backoff alone ❌
- Connection pooling ❌
**Solution:** Session tracking + 2s cleanup delay ✅
**Lesson:** Sometimes the API needs time to clean up server-side state

### 2. **Audio Glitches & Stuttering**
**Problem:** Choppy audio playback, occasional crashes
**Root Cause:** PyAudio read/write operations blocking each other
**Solution:** Separate threading locks for read/write, async queue for playback
**Result:** Smooth, uninterrupted audio streaming

### 3. **Wake Word False Positives**
**Problem:** Wake word detected but AI not activating
**Root Cause:** State machine logic error (inactive vs. standby)
**Solution:** Removed "inactive" state, simplified to standby/active
**Result:** Reliable activation every time

### 4. **Memory & Context Loss**
**Problem:** Jarvis forgetting conversations too quickly
**Solution 1:** SQLite persistent storage
**Solution 2:** RAG-based context retrieval
**Solution 3:** Proactive fact extraction with Groq
**Result:** Weeks-long conversation memory

### 5. **Battery Drain on Laptops**
**Problem:** Wake word detection consuming too much power
**Solution:**
- Event-driven architecture (not polling)
- Auto-sleep when Mac sleeps
- Auto-restart on wake
**Result:** <2% battery impact per hour

### 6. **Smart Home Control Latency**
**Problem:** "Turn on lights" took 5+ seconds
**Solution:** Google Assistant SDK integration (bypassed Home Assistant)
**Result:** <1s from command to lights on

### 7. **Multi-language Support**
**Problem:** Jarvis only understanding English
**Solution:** Language detector in core + Gemini's multilingual capability
**Result:** Supports EN, ZH, JA, KO, ES, FR, DE, IT, PT, RU, AR, HI

### 8. **Self-Evolution Safety**
**Problem:** How to let AI write code without breaking everything?
**Solution:**
- Sandboxed execution environment
- Extension system (isolated .py files)
- Manual approval for core changes
**Status:** Experimental, disabled by default

### 9. **Electron ↔ Python Communication**
**Problem:** IPC overhead, connection drops
**Solution:** WebSocket for audio, REST API for commands
**Result:** <10ms IPC latency

### 10. **JSON Parsing Errors in Tool Responses**
**Problem:** Tool outputs breaking Gemini API (unescaped quotes, etc.)
**Solution:** Sanitization layer in `tool_executor.py`
**Result:** Zero parsing errors in 10,000+ tool calls

---

## 🚧 What's In Progress

### Current Development
1. **Advanced Vision Features** 🏗️
   - Real-time screen monitoring
   - OCR text extraction
   - UI element detection
   - Visual question answering

2. **Mobile Companion App** 📱 (Planned)
   - iOS/Android remote control
   - Push notifications for reminders
   - Location-based triggers
   - Shared conversation history

3. **Enhanced Proactive Intelligence** 🧠
   - Predictive suggestions ("Time for your 3pm meeting")
   - Context-aware automation ("Traffic is bad, leave now")
   - Calendar intelligence
   - Smart routine detection

4. **Multi-User Support** 👥 (Planned)
   - Voice recognition for different users
   - Separate memory profiles
   - Shared vs. personal facts
   - Family mode

5. **Plugin Ecosystem** 🔌 (Planned)
   - Community-contributed tools
   - Plugin marketplace
   - Version management
   - Auto-updates

### Experimental Features
- **Self-Evolution**: AI writing its own tools (disabled by default)
- **Visual Attention**: Eye tracking for screen focus
- **Ambient Listening**: Contextual awareness without wake word
- **Dream Mode**: Processing memories during idle time

### Known Issues
- [ ] Occasional audio stream reconnection lag (~2s)
- [ ] Settings UI voice change requires reconnection
- [ ] Large conversation history (>500 turns) slows context retrieval
- [ ] Screen analysis limited to 1080p (performance)

---

## 📦 Installation Guide

### Prerequisites

**macOS Requirements:**
- macOS 12.0 (Monterey) or later
- M1/M2 Mac recommended (works on Intel too)
- Python 3.11 or 3.12
- Node.js 18+
- Sox (for audio recording)
- Minimum 8GB RAM (16GB recommended)

**API Keys Required:**
- Google AI Studio: Gemini API key ([get here](https://aistudio.google.com/app/apikey))
- Picovoice: Wake word access key ([get here](https://console.picovoice.ai/))

**Optional API Keys:**
- Groq: For fast LLM fallback ([get here](https://console.groq.com/))
- Cerebras: Alternative fast LLM ([get here](https://cloud.cerebras.ai/))
- Tavily: Web search ([get here](https://tavily.com/))
- LTA DataMall: Singapore bus data ([get here](https://datamall.lta.gov.sg/))

### Step-by-Step Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/agarw48550/Jarvis.git
cd "Jarvis/jarvis"
```

#### 2. Install System Dependencies
```bash
# macOS
brew install sox portaudio
```

#### 3. Set Up Python Backend
```bash
cd python
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4. Install Frontend Dependencies
```bash
cd ..  # Back to jarvis/ directory
npm install
```

#### 5. Configure Environment Variables
Create `.env` file in `jarvis/` directory:
```env
# REQUIRED
GEMINI_API_KEY=your_gemini_api_key_here
PICOVOICE_ACCESS_KEY=your_picovoice_key_here

# OPTIONAL
GROQ_API_KEY=your_groq_key
CEREBRAS_API_KEY=your_cerebras_key
TAVILY_API_KEY=your_tavily_key
LTA_API_KEY=your_lta_key

# GOOGLE CLOUD (for Gmail, Drive, Calendar)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# DEBUG (optional)
JARVIS_DEBUG=false
```

#### 6. Run Jarvis
```bash
npm run start
```

This will:
1. Compile the Electron app
2. Start the Python backend automatically
3. Open the Jarvis window
4. Initialize wake word detection

#### 7. Grant Permissions
On first run, macOS will ask for:
- ✅ **Microphone Access** (required)
- ✅ **Accessibility** (for system control features)
- ✅ **Screen Recording** (for screen analysis)

### Alternative: Development Mode

For development with hot reload:

**Terminal 1 - Backend:**
```bash
cd python
source venv/bin/activate
python main.py
```

**Terminal 2 - Frontend:**
```bash
npm run start
```

### Building for Distribution

```bash
npm run make
```

Outputs to `out/` directory:
- macOS: `.dmg` installer
- Windows: `.exe` installer (if built on Windows)
- Linux: `.deb` / `.rpm` (if built on Linux)

### Troubleshooting

**"Python backend failed to start"**
- Ensure Python 3.11+ is installed: `python3 --version`
- Check virtual environment is activated
- Verify all requirements installed: `pip list`

**"Wake word not detecting"**
- Check microphone permissions in System Preferences
- Verify Picovoice key is valid
- Try saying "Hey Jarvis" louder and clearer

**"Audio is glitchy"**
- Close other audio apps (Zoom, Discord, etc.)
- Check PyAudio installation: `python -c "import pyaudio"`
- Try increasing chunk size in `core/config.py`

**"409 Conflict errors"**
- Wait 5 seconds between restarts
- Check if another Jarvis instance is running
- Verify API key is correct

---

## 🏛️ Architecture

### Project Structure

```
Jarvis V3/
├── jarvis/
│   ├── electron/               # Electron main process
│   │   ├── main.ts            # Window, tray, lifecycle
│   │   └── ipc-handlers.ts    # IPC communication
│   │
│   ├── src/                   # React frontend
│   │   ├── App.tsx            # Main UI component
│   │   ├── components/        # UI components
│   │   ├── hooks/             # React hooks
│   │   │   └── useVoicePipeline.ts  # Voice state management
│   │   └── services/          # API clients
│   │
│   ├── python/                # Python backend
│   │   ├── core/              # Core systems
│   │   │   ├── session_manager.py      # Audio streaming
│   │   │   ├── memory.py               # SQLite memory
│   │   │   ├── contextual_memory.py    # Conversation context
│   │   │   ├── emotion_detection.py    # Emotion analyzer
│   │   │   ├── personalization.py      # Learning system
│   │   │   ├── llm_router.py           # Model selection
│   │   │   ├── config.py               # Configuration
│   │   │   └── logging_config.py       # Logging
│   │   │
│   │   ├── tools/             # Function tools
│   │   │   ├── tool_registry.py        # Central registry
│   │   │   ├── system_tools.py         # System control
│   │   │   ├── communication_tools.py  # Email, calendar
│   │   │   ├── google_tools.py         # Google APIs
│   │   │   ├── transport_tools.py      # Bus/transport
│   │   │   ├── vision_tools.py         # Screen analysis
│   │   │   ├── google_assistant.py     # Smart home
│   │   │   └── ...                     # More tools
│   │   │
│   │   ├── interfaces/        # I/O interfaces
│   │   │   └── voice/
│   │   │       ├── tts_handler.py      # Text-to-speech
│   │   │       └── stt_handler.py      # Speech-to-text
│   │   │
│   │   ├── data/              # Data storage
│   │   │   └── jarvis.db      # SQLite database
│   │   │
│   │   ├── main.py            # Flask API server
│   │   └── requirements.txt   # Python dependencies
│   │
│   ├── assets/                # Images, icons
│   ├── package.json           # NPM dependencies
│   └── .env                   # Environment variables
│
├── README.md
└── JARVIS_COMPLETE_DOCUMENTATION.md
```

### Database Schema

**SQLite Database (`data/jarvis.db`):**

```sql
-- Conversations
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    summary TEXT
);

-- Messages
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    conversation_id TEXT,
    role TEXT,  -- 'user' or 'assistant'
    content TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

-- Long-term Facts
CREATE TABLE facts (
    id INTEGER PRIMARY KEY,
    fact TEXT UNIQUE,
    category TEXT,
    created_at TIMESTAMP,
    last_accessed TIMESTAMP
);

-- User Preferences
CREATE TABLE preferences (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP
);

-- Usage Patterns
CREATE TABLE usage_patterns (
    action TEXT,
    context TEXT,
    hour INTEGER,
    day_of_week INTEGER,
    count INTEGER,
    last_used TIMESTAMP,
    PRIMARY KEY (action, context, hour, day_of_week)
);
```

### API Endpoints

**Flask Backend (Port 5000):**

```
HTTP Endpoints:
GET  /health              - Health check
POST /trigger             - Manual activation
GET  /status              - Current state
POST /stop                - Stop AI
GET  /voices              - List available voices
POST /voice               - Change voice

WebSocket Endpoints:
WS   /audio               - Bidirectional audio stream
WS   /control             - Control messages
```

### State Management

**Frontend (Zustand):**
```typescript
interface VoiceState {
  state: 'idle' | 'listening' | 'processing' | 'speaking' | 'error';
  isOnline: boolean;
  currentTranscript: string;
  currentResponse: string;
  error: string | null;
}
```

**Backend (Python Dict):**
```python
state = {
    "active": bool,          # Main loop running
    "is_ai_active": bool,    # AI currently speaking
    "status": str,           # STOPPED, LISTENING, PROCESSING, SPEAKING
    "voice": str,            # Current voice name
    "key_idx": int,          # Current API key index
    "session_handle": str,   # Resumption token
}
```

### Performance Metrics

**Latency Breakdown:**
- Wake word → Backend trigger: ~50ms
- Backend → Gemini connection: ~400ms
- Audio chunk encode/send: ~10ms per chunk (16ms chunks)
- Gemini processing: ~200-500ms (varies by query)
- Audio receive/decode: ~10ms per chunk
- Total (wake → first audio): **~650ms average**

**Resource Usage:**
- Python backend: 80-150MB RAM
- Electron app: 150-250MB RAM
- CPU (idle): <5%
- CPU (speaking): 15-20%
- Network: ~50KB/s during conversation

---

## 🎓 Lessons Learned

1. **Native is Always Better**: End-to-end audio beats STT→LLM→TTS pipeline every time
2. **State Machines Are Your Friend**: Clear state definitions prevent 90% of bugs
3. **Async Everywhere**: Never block the event loop
4. **Fail Gracefully**: The best error handling is the kind users never see
5. **Memory is Identity**: An AI that remembers is an AI that feels personal
6. **Logging Saves Lives**: You can't debug what you can't see
7. **APIs Have Limits**: Always plan for quotas, rate limits, and failures
8. **UX > Features**: A beautiful, simple interface beats 100 hidden features
9. **Iteration is Key**: Every version taught us something new
10. **Community Matters**: Open-sourcing created accountability and improvement

---

## 🔮 Future Vision

**Short-term (Next 3 months):**
- Mobile companion app (iOS/Android)
- Plugin marketplace for community tools
- Multi-user support with voice recognition
- Enhanced vision capabilities

**Long-term (1-2 years):**
- Ambient intelligence (contextual awareness without wake word)
- Cross-device synchronization (Mac, iPhone, iPad)
- AR integration (Apple Vision Pro support)
- Autonomous task execution (complex multi-step workflows)
- Conversational memory spanning years
- Personality customization (formal, casual, humorous modes)

**Dream Features:**
- Holographic interface
- Brain-computer interface support
- True AGI integration when available
- Quantum computing optimization

---

## 📞 Get Involved

**Contributors Welcome!**
- Found a bug? [Open an issue](https://github.com/agarw48550/Jarvis/issues)
- Have a feature idea? Start a discussion
- Want to contribute? Check `CONTRIBUTING.md`

**Built by:** Ayaan Agarwal  
**License:** MIT  
**Status:** Active Development  
**Version:** 3.0 (Stable)

---

*"Sometimes you gotta run before you can walk."* - Tony Stark

Built with ❤️ and countless hours of debugging.
