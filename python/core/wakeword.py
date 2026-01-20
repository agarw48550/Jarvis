
import os
import struct
import pvporcupine
import pvrecorder
import threading
from dotenv import load_dotenv

load_dotenv()

class WakeWordListener:
    def __init__(self, callback, keyword_path=None, sensitivity=0.5):
        self.access_key = os.getenv("PICOVOICE_ACCESS_KEY")
        
        # Default to the bundled file if not provided
        if not keyword_path:
            # First check if the specific file exists in the workspace root
            # Based on user's feedback and find results:
            # ./Hey-Boo-V_en_mac_v4_0_0/Hey-Boo-V_en_mac_v4_0_0.ppn
            base_dir = os.path.dirname(os.path.abspath(__file__)) # jarvis/python/core
            root_dir = os.path.dirname(os.path.dirname(os.path.dirname(base_dir)))
            
            possible_path = os.path.join(root_dir, "Hey-Boo-V_en_mac_v4_0_0", "Hey-Boo-V_en_mac_v4_0_0.ppn")
            if os.path.exists(possible_path):
                keyword_path = possible_path
            else:
                # Search for the .ppn file specifically in a way that prioritizes the macOS one
                for root, dirs, files in os.walk(root_dir):
                    # Skip venv to avoid picking up the raspberry-pi one from site-packages
                    if 'venv' in root or '.venv' in root or 'node_modules' in root:
                        continue
                    for file in files:
                        if file.endswith(".ppn") and "mac" in file.lower():
                            keyword_path = os.path.join(root, file)
                            break
                    if keyword_path: break
            
        self.keyword_path = keyword_path
        self.callback = callback
        self.sensitivity = sensitivity
        self.running = False
        self.thread = None
        self.recorder = None
        self.porcupine = None

    def start(self):
        if self.running:
            return

        # Ensure access key is available at start time
        if not self.access_key:
            self.access_key = os.getenv("PICOVOICE_ACCESS_KEY")
            
        if not self.access_key:
            raise ValueError("PICOVOICE_ACCESS_KEY not found in .env")

        try:
            if self.keyword_path:
                print(f"🔄 [WAKEWORD] Creating Porcupine with custom path: {self.keyword_path}")
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keyword_paths=[self.keyword_path],
                    sensitivities=[self.sensitivity]
                )
            else:
                # Fallback to built-in 'jarvis' if custom file not found
                print("⚠️ [WAKEWORD] No custom .ppn file found. Falling back to built-in 'jarvis'.")
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=['jarvis'],
                    sensitivities=[self.sensitivity]
                )

            # Try to pick a sensible default device if -1 fails or is generic
            # Sometimes 'MacBook Air Microphone' is more reliable than system default
            devices = pvrecorder.PvRecorder.get_available_devices()
            device_index = -1
            for i, d in enumerate(devices):
                if "MacBook Air Microphone" in d:
                    device_index = i
                    break

            self.recorder = pvrecorder.PvRecorder(
                device_index=device_index, 
                frame_length=self.porcupine.frame_length
            )
            
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            print(f"👂 [WAKEWORD] Listening for wake word ({os.path.basename(self.keyword_path) if self.keyword_path else 'jarvis'})...")

        except Exception as e:
            print(f"❌ [WAKEWORD] Failed to initialize: {e}")
            self.cleanup()
            raise e

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            if threading.current_thread() != self.thread:
                self.thread.join(timeout=2.0)
        self.cleanup()
        print("🛑 [WAKEWORD] Stopped.")

    def cleanup(self):
        if self.recorder:
            try:
                self.recorder.stop()
            except: pass
            try:
                self.recorder.delete()
            except: pass
            self.recorder = None
        
        if self.porcupine:
            try:
                self.porcupine.delete()
            except: pass
            self.porcupine = None

    def _listen_loop(self):
        try:
            self.recorder.start()
            while self.running:
                pcm = self.recorder.read()
                result = self.porcupine.process(pcm)
                
                if result >= 0:
                    print("⚡ [WAKEWORD] Detected!")
                    if self.callback:
                        self.callback()
                        
        except Exception as e:
            if self.running:
                print(f"❌ [WAKEWORD] Error in loop: {e}")

