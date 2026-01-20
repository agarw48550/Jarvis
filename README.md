# 🤖 JARVIS V3 - Your Advanced Virtual Assistant

<div align="center">
  <img src="jarvis/assets/hero.png" width="800" alt="Jarvis V3 Hero">
  <p><i>The futuristic, low-latency, and modular AI companion for your desktop.</i></p>

  [![Build Status](https://img.shields.io/badge/Build-v4--Stable-blue?style=for-the-badge&logoColor=white)](https://github.com/agarw48550/Jarvis)
  [![Models](https://img.shields.io/badge/Models-Gemini--2.0--Flash-88ddff?style=for-the-badge&logo=google-gemini)](https://ai.google.dev/)
  [![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
</div>

---

## ✨ Overview

**Jarvis V3** is a state-of-the-art virtual assistant built with a focus on speed, modularity, and seamless user interaction. It combines the power of **Google Gemini 2.0 Flash** with a high-performance **Native Audio Pipeline** to provide a truly responsive "Live" conversation experience.

Whether you're looking for real-time information, system control, or a companion to brainstorm with, Jarvis V3 is designed to live in your system tray and react to your every word.

---

## 🚀 Key Features

- 🎙️ **Native Audio Pipeline**: Ultra-low latency bidirectional audio streaming via WebSockets.
- ⚡ **Gemini Live Integration**: Powered by the Gemini 2.0 Flash model for lightning-fast responses and multimodal reasoning.
- 👂 **Wake Word Detection**: Crystal clear "Hey Jarvis" detection using **Picovoice Porcupine**.
- 🛠️ **Modular Tool System**: 
  - 🚌 **Transport**: Real-time SG Bus arrivals and location services.
  - 🍱 **System Control**: Media playback, volume control, and app management.
  - 🧠 **Contextual Memory**: SQLite-backed memory for facts, preferences, and usage patterns.
  - 🖥️ **Vision**: Integrated screen analysis and vision-based environment awareness.
- 🎨 **Sleek UI/UX**: Electron-based frameless window with a reactive "Voice Orb" and glassmorphism design.
- 🔄 **Autonomous Evolution**: Self-improving system prompt and model load balancing.

---

## 🏗️ Technical Stack

- **Frontend**: [React](https://reactjs.org/) + [Vite](https://vitejs.dev/) + [Tailwind CSS](https://tailwindcss.com/)
- **Desktop Wrapper**: [Electron](https://www.electronjs.org/)
- **Backend API**: [Python](https://www.python.org/) + [Flask](https://flask.palletsprojects.com/) + [Flask-Sock](https://github.com/miguelgrinberg/flask-sock)
- **AI Core**: [Google Generative AI SDK](https://github.com/google/generative-ai-python)
- **Database**: SQLite3 (Conversational & Contextual Memory)
- **Animations**: [Framer Motion](https://www.framer.com/motion/)

---

## 🛠️ Installation

### 1. Prerequisites
- **Python 3.11+**
- **Node.js 18+**
- **Sox** (for audio recording functionality)
  ```bash
  brew install sox  # (macOS)
  ```

### 2. Clone & Setup
```bash
git clone https://github.com/agarw48550/Jarvis.git
cd Jarvis/jarvis
```

### 3. Backend Setup
```bash
cd python
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Frontend Setup
```bash
cd ..
npm install
```

### 5. Environment Variables
Create a `.env` file in the `jarvis/` directory:
```env
GOOGLE_API_KEY=your_gemini_api_key
PICOVOICE_ACCESS_KEY=your_ppn_key
LTA_API_KEY=your_lta_datamall_key
TAVILY_API_KEY=your_tavily_key
```

---

## 🖱️ Usage

### Development
Start the application in development mode:
```bash
npm run start
```
*The Electron app will launch and automatically spawn the Python backend.*

### Using the Tray
- **Left-Click**: Toggle the Jarvis window.
- **Right-Click**: Access the Context Menu (Restart Backend, Quit, Configure Access).

---

## 🛠️ Roadmap & Status

| Feature | Status |
| :--- | :--- |
| **Bidirectional Audio** | ✅ Completed |
| **System Tooling** | ✅ Completed |
| **Gemini 2.0 Integration**| ✅ Completed |
| **Voice Selection UI** | ✅ Completed |
| **Contextual Memory** | ✅ Completed |
| **Advanced Vision** | 🏗️ In Progress |
| **Mobile Companion** | 🏗️ Planned |

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
  <p>Built with ❤️ by Ayaan Agarwal</p>
  <p><i>"I am Iron Man."</i></p>
</div>
