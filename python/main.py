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

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app)

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
            "wake_word":  "ready",
            "stt": "ready",
            "tts": "ready"
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

# ============== Speech-to-Text (Whisper) ==============
@app.route('/stt/transcribe', methods=['POST'])
def transcribe():
    try: 
        from stt.whisper_service import transcribe_audio
        
        data = request.get_json()
        
        # Handle base64 audio data
        if 'audio_base64' in data: 
            audio_bytes = base64.b64decode(data['audio_base64'])
            temp_file = TEMP_DIR / 'input_audio.wav'
            with open(temp_file, 'wb') as f:
                f.write(audio_bytes)
            text = transcribe_audio(str(temp_file))
        elif 'audio_path' in data: 
            text = transcribe_audio(data['audio_path'])
        else:
            return jsonify({"error":  "No audio provided", "success": False}), 400
        
        print(f"📝 Transcribed:  {text}")
        return jsonify({"text": text, "success": True})
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error":  str(e), "success": False}), 500

# ============== Text-to-Speech (Piper) ==============
@app.route('/tts/speak', methods=['POST'])
def speak():
    global current_voice
    
    try: 
        from tts.piper_service import text_to_speech, play_audio
        
        data = request.get_json()
        text = data.get('text', '')
        voice = data.get('voice', current_voice)
        play_immediately = data.get('play', True)
        
        if not text: 
            return jsonify({"error": "No text provided", "success": False}), 400
        
        print(f"🔊 Speaking: {text[: 50]}...")
        
        audio_path = text_to_speech(text, voice)
        
        if play_immediately:
            play_audio(audio_path)
        
        return jsonify({
            "audio_path": audio_path,
            "success": True
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/tts/voices', methods=['GET'])
def get_voices():
    voices = [
        {"id": "male", "name": "Ryan (Male)", "description": "Clear American male voice"},
        {"id": "female", "name": "Amy (Female)", "description": "Friendly American female voice"}
    ]
    return jsonify({"voices": voices})

@app.route('/tts/set-voice', methods=['POST'])
def set_voice():
    global current_voice
    data = request.get_json()
    current_voice = data.get('voice', 'male')
    return jsonify({"voice": current_voice, "success": True})

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
    print("  POST /wake-word/start - Start wake word detection")
    print("  POST /wake-word/stop  - Stop wake word detection")
    print("  GET  /wake-word/poll  - Poll for detections")
    print("  POST /stt/transcribe  - Transcribe audio to text")
    print("  POST /tts/speak       - Convert text to speech")
    print("  GET  /tts/voices      - List available voices")
    print("  POST /audio/record    - Record audio")
    print()
    print("🚀 Server starting on http://127.0.0.1:5000")
    print("=" * 50)
    
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
