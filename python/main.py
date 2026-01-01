#!/usr/bin/env python3
"""
Jarvis AI Assistant - Python Backend Server
Handles:  Wake Word Detection, Speech-to-Text, Text-to-Speech
"""

import os
import sys
import json
import queue
import threading
import tempfile
import base64
from pathlib import Path

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sock import Sock 
import asyncio
import simple_websocket
from core.gemini_live import GeminiLiveSession

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)
sock = Sock(app)

# ============== Global State ==============
wake_detector = None
is_listening = False
detection_queue = queue.Queue()
current_voice = 'male'

# ============== Paths ==============
BASE_DIR = Path(__file__).parent.parent
VOICES_DIR = BASE_DIR / 'assets' / 'voices'
TEMP_DIR = Path(tempfile.gettempdir()) / 'jarvis'
TEMP_DIR.mkdir(exist_ok=True)

# ============== Health Check ==============
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "listening": is_listening,
        "services": {
            "gemini_live": "active",
            "search_grounding": "native"
        }
    })

# ============== Wake Word Detection ==============
@app.route('/wake-word/start', methods=['POST'])
def start_wake_word():
    global wake_detector, is_listening
    
    try:
        if is_listening:
            return jsonify({"status": "already_listening"})
        
        from wake_word.detector import WakeWordDetector
        
        def on_detection(keyword):
            detection_queue.put({"detected": True, "keyword": keyword})
            print(f"✨ Wake word detected:  {keyword}")
        
        if wake_detector is None:
            wake_detector = WakeWordDetector(
                wake_words=["hey_jarvis"],
                callback=on_detection,
                threshold=0.5
            )
        
        is_listening = True
        thread = threading.Thread(target=wake_detector.start_listening, daemon=True)
        thread.start()
        
        return jsonify({"status": "started"})
        
    except Exception as e: 
        import traceback
        traceback.print_exc()
        return jsonify({"status":  "error", "message": str(e)}), 500

@app.route('/wake-word/stop', methods=['POST'])
def stop_wake_word():
    global wake_detector, is_listening
    
    try:
        if wake_detector:
            wake_detector.stop_listening()
        is_listening = False
        return jsonify({"status": "stopped"})
    except Exception as e: 
        return jsonify({"status": "error", "message":  str(e)}), 500

@app.route('/wake-word/poll', methods=['GET'])
def poll_wake_word():
    try:
        result = detection_queue.get_nowait()
        return jsonify(result)
    except queue.Empty:
        return jsonify({"detected": False})

@sock.route('/ws/live')
def live_audio_socket(ws):
    """
    WebSocket endpoint for bidirectional audio streaming with Gemini Live.
    Client sends PCM audio -> Python -> Gemini
    Gemini sends Audio/Text -> Python -> Client
    """
    global current_session
    
    print("🔌 Client connected to Live Socket")
    
    try:
        # Initialize Session
        current_session = GeminiLiveSession()
        stop_event = asyncio.Event()
        
        # Async helper to run the loop
        async def run_session():
            await current_session.connect(system_instruction=build_system_prompt())
            
            # Setup callbacks
            def on_audio(pcm_data):
                # Send back to client
                try:
                    # Convert to base64 for safe transport over WS (or send bytes if client supports)
                    # For simplicity, text frame with base64
                    ws.send(json.dumps({
                        "type": "audio",
                        "data": base64.b64encode(pcm_data).decode("utf-8")
                    }))
                except Exception as e:
                    print(f"WS Send Error: {e}")

            def on_text(text):
                ws.send(json.dumps({
                    "type": "text",
                    "data": text
                }))

            # Start receive loop (non-blocking in async context)
            # But we are in a synchronous Flask route wrapper?
            # flask-sock runs in a thread. We need a way to run async code here.
            # We can use asyncio.run or create a loop.
            
            await current_session.receive_loop(on_audio, on_text)

        # Run async loop in this thread
        # WebSocket loop for converting Client input -> Session.send_audio
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Start connection
        loop.run_until_complete(current_session.connect(system_instruction=build_system_prompt()))
        
        # We need to run receive_loop concurrently with reading client input
        # So we create a task
        receive_task = loop.create_task(current_session.receive_loop(
            lambda raw: ws.send(json.dumps({"type": "audio", "data": base64.b64encode(raw).decode('utf-8')})),
            lambda txt: ws.send(json.dumps({"type": "text", "data": txt}))
        ))
        
        try:
            while True:
                # Read from Client
                message = ws.receive()
                if not message:
                    break
                
                data = json.loads(message)
                if data.get("type") == "audio" and current_session.running:
                    # Audio chunk from client (base64)
                    pcm = base64.b64decode(data["data"])
                    # Send to Gemini
                    loop.run_until_complete(current_session.send_audio_chunk(pcm))
                    
        except simple_websocket.ConnectionClosed:
            pass
        finally:
            loop.run_until_complete(current_session.close())
            loop.close()
            
    except Exception as e:
        print(f"Live Session Error: {e}")
        import traceback
        traceback.print_exc()

# Legacy STT and TTS endpoints removed in favor of Native Audio Dialog


# ============== Audio Recording ==============
@app.route('/audio/record', methods=['POST'])
def record_audio():
    """Record audio for a specified duration or until silence"""
    try:
        from utils.audio import record_until_silence
        
        data = request.get_json() or {}
        max_duration = data.get('max_duration', 10)
        silence_threshold = data.get('silence_threshold', 500)
        silence_duration = data.get('silence_duration', 1.5)
        
        audio_path = record_until_silence(
            max_duration=max_duration,
            silence_threshold=silence_threshold,
            silence_duration=silence_duration
        )
        
        # Read and encode as base64
        with open(audio_path, 'rb') as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')
        
        return jsonify({
            "audio_path": audio_path,
            "audio_base64": audio_base64,
            "success": True
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error":  str(e), "success": False}), 500

# ============== Main ==============
# Add core imports
from core.orchestrator import JarvisOrchestrator
from core.llm_router import chat
from core.memory import add_message, add_fact, get_all_facts
from core.tool_executor import extract_and_execute_tools
from core.gemini_live import build_system_prompt
from tools.tool_registry import TOOLS

orchestrator = JarvisOrchestrator()

# Legacy Text Chat endpoint removed


@app.route('/memory/facts', methods=['GET'])
def get_facts():
    return jsonify({"facts": get_all_facts()})

if __name__ == '__main__':
    print("=" * 50)
    print("🤖 JARVIS Python Backend Starting...")
    print("=" * 50)
    print(f"📁 Base directory: {BASE_DIR}")
    print(f"🎤 Voices directory:  {VOICES_DIR}")
    print(f"📂 Temp directory:  {TEMP_DIR}")
    print()
    print("Available endpoints:")
    print("  GET  /health          - Check server status")
    print("  WS   /ws/live         - Native Audio WebSocket")
    print("  GET  /memory/facts    - Get remembered facts")

    print()
    print("🚀 Server starting on http://127.0.0.1:5001")
    print("=" * 50)
    
    app.run(host='127.0.0.1', port=5001, debug=False, threaded=True)
