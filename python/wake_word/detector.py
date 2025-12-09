#!/usr/bin/env python3
"""Wake Word Detection using OpenWakeWord"""

import numpy as np
import threading
import time

class WakeWordDetector:
    def __init__(self, wake_words=None, callback=None, threshold=0.5):
        self.wake_words = wake_words or ["hey_jarvis"]
        self.callback = callback
        self.threshold = threshold
        self.is_running = False
        self._stop_event = threading.Event()
        self.model = None
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize OpenWakeWord model"""
        try: 
            from openwakeword.model import Model
            print("Loading wake word models...")
            
            # Try to use built-in models first
            self.model = Model(
                wakeword_models=self.wake_words,
                inference_framework="onnx"
            )
            print(f"✅ Wake word detector ready.  Listening for:  {self.wake_words}")
            
        except Exception as e:
            print(f"⚠️ Could not load custom wake word, using default 'hey jarvis'")
            print(f"   Error: {e}")
            
            # Fallback:  try loading without specific wake words
            try: 
                from openwakeword.model import Model
                self.model = Model(inference_framework="onnx")
                self.wake_words = list(self.model.models.keys())
                print(f"✅ Loaded default models:  {self.wake_words}")
            except Exception as e2:
                print(f"❌ Failed to load any wake word model: {e2}")
                raise
    
    def start_listening(self):
        """Start listening for wake word (blocking)"""
        import pyaudio
        
        if self.model is None:
            print("❌ No model loaded, cannot start listening")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        CHUNK = 1280  # ~80ms at 16kHz
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = pyaudio.PyAudio()
        
        try:
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            print("🎤 Listening for wake word...")
            
            while not self._stop_event.is_set():
                try: 
                    audio_data = stream.read(CHUNK, exception_on_overflow=False)
                    audio_array = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Get predictions
                    predictions = self.model.predict(audio_array)
                    
                    # Check each wake word
                    for wake_word, score in predictions.items():
                        if score > self.threshold:
                            print(f"✨ Detected '{wake_word}' with confidence {score:.2f}")
                            
                            if self.callback:
                                self.callback(wake_word)
                            
                            # Reset model state and pause briefly
                            self.model.reset()
                            time.sleep(1.0)
                            break
                            
                except Exception as e:
                    if not self._stop_event.is_set():
                        print(f"Audio read error: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Wake word detection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                stream.stop_stream()
                stream.close()
            except: 
                pass
            p.terminate()
            self.is_running = False
            print("🛑 Wake word detection stopped")
    
    def stop_listening(self):
        """Stop listening for wake word"""
        self._stop_event.set()
        self.is_running = False
