# 🤖 JARVIS V3 - Your Advanced Virtual Assistant

<div align="center">
  <img src="jarvis/assets/hero.png" width="800" alt="Jarvis V3 Hero">
  <p><i>The futuristic, low-latency, and modular AI companion for your desktop.</i></p>

  [![Build Status](https://img.shields.io/badge/Build-v3.0--Stable-blue?style=for-the-badge&logoColor=white)](https://github.com/agarw48550/Jarvis)
  [![Models](https://img.shields.io/badge/Models-Gemini--2.5--Flash-88ddff?style=for-the-badge&logo=google-gemini)](https://ai.google.dev/)
  [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
  ![Platform](https://img.shields.io/badge/Platform-macOS-lightgrey?style=for-the-badge&logo=apple)
</div>

---

## ✨ Overview

**Jarvis V3** is an advanced AI virtual assistant inspired by Tony Stark's JARVIS - a truly intelligent companion that lives on your Mac, always ready to help. Built with cutting-edge technology, it features:

- 🎙️ **Ultra-Low Latency Audio**: ~650ms wake-to-response via native audio streaming
- 🧠 **Contextual Memory**: Remembers you across sessions with SQLite + RAG
- 👂 **Always Listening**: "Hey Jarvis" wake word activation
- 🏠 **Smart Home Control**: Google Assistant integration
- 🌐 **80+ Tools**: System control, web search, emails, calendar, transport, and more
- 💎 **Beautiful UI**: Glassmorphic design with animated voice orb
- 🔄 **Self-Learning**: Proactive fact extraction and personalization

> 📖 **[Read the Complete Documentation](JARVIS_COMPLETE_DOCUMENTATION.md)** for full feature list, development history, and architecture details.

---

## 🚀 Complete Feature List

### 🎯 Core Capabilities
- ✅ **Native Audio Streaming** - Bidirectional 16kHz/24kHz audio via WebSocket
- ✅ **Wake Word Detection** - "Hey Jarvis" activation with Picovoice Porcupine
- ✅ **Multiple Voices** - Puck, Charon, Fenrir, Aoede, Kore
- ✅ **Contextual Memory** - SQLite database with RAG for long-term recall
- ✅ **Emotion Detection** - Adapts tone based on detected emotions
- ✅ **Proactive Learning** - Automatic fact extraction from conversations
- ✅ **Smart Model Router** - Switches between Gemini/Groq/Cerebras based on complexity

### 🛠️ System Control (10 tools)
- Open/close applications
- Volume control (set, mute, up/down)
- Brightness adjustment
- Battery status
- Media playback (play/pause/next/previous for any app)
- Screenshot capture
- Process monitoring
- Screen analysis (vision)

### 📧 Productivity (15 tools)
- **Email**: Send/read Gmail messages
- **Calendar**: View events, create entries
- **Reminders**: Add, list, clear
- **Timers**: Set multiple named timers
- **Time/Date**: Current time, timezone lookup

### 🌐 Information & Web (20 tools)
- **Web Search**: Tavily-powered search
- **News**: Latest news on any topic
- **Weather**: Current conditions for any city
- **Calculations**: Math expression evaluation
- **Google Drive**: List, search files
- **Google Classroom**: View courses, assignments
- **Contacts**: Google Contacts search
- **Maps**: Directions, places nearby, geocoding
- **Timezone**: Lookup for any location

### 🚌 Singapore Transport (6 tools)
- Real-time bus arrivals (LTA DataMall)
- Bus stop search by name/road
- Nearby buses from saved location
- Home location management
- Distance calculations

### 🏠 Smart Home (1 tool)
- **Google Assistant**: Control lights, switches, thermostats via natural language

### 🤖 AI & Developer (5 tools)
- Query external LLMs (Groq, Cerebras)
- Write custom Python extensions
- Run Python code in sandbox
- List installed extensions

### 🧠 Memory & Learning (5 tools)
- Add/delete facts
- Search memories
- Search conversations (weeks back)
- Get/set preferences
- View memory stats

**Total: 80+ Tools across 10+ Categories**

---

## 🏗️ Technical Stack

**Frontend:**
- React 19 + TypeScript
- Framer Motion (animations)
- Tailwind CSS (styling)
- Zustand (state management)
- Electron 39 (desktop wrapper)

**Backend:**
- Python 3.11+
- Flask + Flask-Sock (WebSocket server)
- Google Generative AI SDK
- PyAudio (audio I/O)
- SQLite3 (persistence)
- NumPy (audio processing)

**APIs & Services:**
- Google Gemini 2.5 Flash (native audio)
- Groq (Llama 3.3 70B)
- Cerebras (Llama 3.3 70B)
- Picovoice Porcupine (wake word)
- Google Workspace APIs (Gmail, Calendar, Drive, Classroom)
- Google Maps APIs (Directions, Places)
- Google Assistant SDK
- LTA DataMall (Singapore Transport)
- Tavily (web search)

---

## 📦 Quick Start

### Prerequisites
- macOS 12.0+ (M1/M2 recommended)
- Python 3.11 or 3.12
- Node.js 18+
- Sox: `brew install sox portaudio`

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/agarw48550/Jarvis.git
cd "Jarvis/jarvis"
```

2. **Set up Python backend**
```bash
cd python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

3. **Install frontend dependencies**
```bash
cd ..
npm install
```

4. **Configure environment**
Create `.env` file in `jarvis/` directory:
```env
# REQUIRED
GEMINI_API_KEY=your_gemini_key_here
PICOVOICE_ACCESS_KEY=your_picovoice_key_here

# OPTIONAL (but recommended)
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
LTA_API_KEY=your_lta_key

# For Google services (Gmail, Drive, etc.)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

5. **Run Jarvis**
```bash
npm run start
```

### Getting API Keys
- **Gemini**: [Google AI Studio](https://aistudio.google.com/app/apikey) (Free)
- **Picovoice**: [Console](https://console.picovoice.ai/) (Free tier available)
- **Groq**: [Console](https://console.groq.com/) (Free tier)
- **Tavily**: [Website](https://tavily.com/) (Free tier)

---

## 🎮 Usage

### Voice Commands Examples
```
"Hey Jarvis, what's the weather?"
"Open Spotify and play some music"
"Send an email to John about the meeting"
"What buses are arriving near me?"
"Turn on the bedroom lights"
"Remind me to call mom tomorrow"
"What's on my calendar today?"
"Search the web for latest AI news"
"Analyze what's on my screen"
"Remember my favorite color is blue"
```

### Interface Controls
- **Say "Hey Jarvis"**: Activate voice assistant
- **Click Voice Orb**: Manual activation
- **System Tray**:
  - Left-click: Show/hide window
  - Right-click: Restart backend, quit
- **Settings**: Change voice, view wake word status
- **Keyboard**: ESC to close modals, Ctrl+C in terminal to quit

---

## 📊 Development History

### The Journey (Late 2025 - Early 2026)

**December 2025:**
- ✅ Built foundation: Electron + React + Python Flask
- ✅ Integrated Gemini 2.0 Flash (text model)
- ✅ Created modular tool system (20+ tools)

**Early January 2026:**
- ✅ **Major Breakthrough**: Discovered Gemini 2.5 Flash native audio
- ✅ Reduced latency from ~3s to <500ms
- ✅ Implemented bidirectional audio streaming

**Mid January 2026:**
- ✅ Solved **409 Conflict Crisis** (session management)
- ✅ Added wake word detection with Picovoice
- ✅ Built contextual memory system (SQLite + RAG)

**Late January 2026:**
- ✅ Integrated 60+ new tools (Google APIs, transport, smart home)
- ✅ Implemented proactive learning with Groq
- ✅ Added emotion detection and adaptive responses
- ✅ Created beautiful glassmorphic UI
- ✅ Achieved 24+ hour uptime stability

### Major Challenges Overcome
1. **409 Conflicts**: Session tracking + cleanup delays
2. **Audio Glitches**: Threading locks + async queues
3. **Memory Loss**: SQLite + RAG + proactive learning
4. **Wake Word Reliability**: State machine simplification
5. **Battery Drain**: Event-driven architecture
6. **Smart Home Latency**: Google Assistant SDK integration

> See [Complete Documentation](JARVIS_COMPLETE_DOCUMENTATION.md) for detailed development timeline and technical decisions.

---

## 🚧 Roadmap & Current Status

### ✅ Completed
- Bidirectional native audio streaming
- Wake word activation
- Contextual memory & learning
- 80+ tool integrations
- Smart home control
- Beautiful UI/UX
- Production stability (24+ hour uptime)
- Multi-language support

### 🏗️ In Progress
- **Advanced Vision**: Real-time screen monitoring, OCR
- **Proactive Intelligence**: Predictive suggestions
- **Performance Optimization**: Further latency reduction

### 📅 Planned
- **Mobile Companion** (iOS/Android)
- **Multi-User Support** (voice recognition)
- **Plugin Ecosystem** (community tools)
- **Enhanced Self-Evolution** (safe AI-written tools)
- **Cross-Device Sync**

---

## 📈 Performance

- **Latency**: ~650ms (wake → first audio)
- **Memory**: <300MB total (Python + Electron)
- **CPU**: <5% idle, <20% during speech
- **Uptime**: 24+ hours stable
- **Audio Quality**: 24kHz, 16-bit PCM

---

## 🤝 Contributing

Contributions are welcome! Whether it's:
- 🐛 Bug reports
- 💡 Feature suggestions
- 📝 Documentation improvements
- 🔧 Code contributions

Please open an issue or pull request on GitHub.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

Built with amazing technologies:
- Google Gemini for incredible AI capabilities
- Picovoice for reliable wake word detection
- The open-source community for inspiration

Special thanks to the Iron Man franchise for the inspiration! 🦾

---

<div align="center">
  <h3>📖 <a href="JARVIS_COMPLETE_DOCUMENTATION.md">Read Complete Documentation</a></h3>
  <p>For architecture details, full feature list, development history, and more</p>
  <br>
  <p>Built with ❤️ by <strong>Ayaan Agarwal</strong></p>
  <p><i>"Sometimes you gotta run before you can walk."</i> - Tony Stark</p>
  <br>
  <p>⭐ Star this repo if you find it useful!</p>
</div>
