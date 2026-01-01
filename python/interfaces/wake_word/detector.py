#!/usr/bin/env python3
"""
Wake Word Detection using OpenWakeWord
Fixed version with better error handling and graceful degradation
"""

import threading
import time
from typing import Optional, Callable

class WakeWordDetector:
    def __init__(self, wake_words=None, callback=None, threshold=0.5):
        self.wake_words = wake_words or ["hey_jarvis"]
        self.callback = callback
        self.threshold = threshold
        self.is_running = False
        self._stop_event = threading.Event()
        self.model = None
        self.error_message = None
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialize OpenWakeWord model with error handling"""
        try: 
            from openwakeword.model import Model
            print("Loading wake word models...")
            
            # Try to use built-in models first
            try:
                self.model = Model(
                    wakeword_models=self.wake_words,
                    inference_framework="onnx"
                )
                print(f"✅ Wake word detector ready. Listening for: {self.wake_words}")
                self.error_message = None
                return
            except Exception as e1:
                print(f"⚠️ Could not load custom wake word '{self.wake_words}', trying defaults...")
                print(f"   Error: {str(e1)[:100]}")
                
                # Fallback: try loading without specific wake words
                try: 
                    self.model = Model(inference_framework="onnx")
                    self.wake_words = list(self.model.models.keys())
                    print(f"✅ Loaded default models: {self.wake_words}")
                    self.error_message = None
                    return
                except Exception as e2:
                    print(f"⚠️ Could not load default models: {str(e2)[:100]}")
                    raise e2
                    
        except ImportError as e:
            error_msg = "openwakeword package not installed. Install with: pip install openwakeword"
            print(f"❌ {error_msg}")
            self.error_message = error_msg
            self.model = None
        except Exception as e:
            error_msg = f"Failed to load wake word model: {str(e)[:200]}"
            print(f"❌ {error_msg}")
            self.error_message = error_msg
            self.model = None
    
    def is_available(self) -> bool:
        """Check if wake word detection is available"""
        return self.model is not None
    
    def get_error(self) -> Optional[str]:
        """Get error message if initialization failed"""
        return self.error_message
    
    def start_listening(self):
        """Start listening for wake word (blocking)"""
        if self.model is None:
            error = self.error_message or "No model loaded"
            print(f"❌ Cannot start wake word detection: {error}")
            return
        
        try:
            import pyaudio
            import numpy as np
        except ImportError as e:
            print(f"❌ Missing dependency: {e}")
            print("   Install with: pip install pyaudio numpy")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        CHUNK = 1280  # ~80ms at 16kHz
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = None
        stream = None
        
        try:
            p = pyaudio.PyAudio()
            
            # Check for available input devices
            try:
                default_input = p.get_default_input_device_info()
            except OSError:
                print("❌ No microphone found. Please check microphone permissions.")
                print("   On macOS: System Settings > Privacy & Security > Microphone")
                self.is_running = False
                return
            
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
                                try:
                                    self.callback(wake_word)
                                except Exception as e:
                                    print(f"⚠️ Callback error: {e}")
                            
                            # Reset model state and pause briefly
                            self.model.reset()
                            time.sleep(1.0)
                            break
                            
                except OSError as e:
                    if not self._stop_event.is_set():
                        if "Input overflowed" in str(e):
                            # Ignore overflow errors, they're common
                            continue
                        print(f"⚠️ Audio read error: {e}")
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        print(f"⚠️ Prediction error: {e}")
                    continue
                    
        except OSError as e:
            if "Input overflowed" not in str(e):
                print(f"❌ Audio device error: {e}")
                print("   Check microphone permissions in System Settings")
        except Exception as e:
            print(f"❌ Wake word detection error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            try:
                if stream:
                    stream.stop_stream()
                    stream.close()
            except: 
                pass
            try:
                if p:
                    p.terminate()
            except:
                pass
            self.is_running = False
            print("🛑 Wake word detection stopped")
    
    def stop_listening(self):
        """Stop listening for wake word"""
        self._stop_event.set()
        self.is_running = False
    
    def is_listening(self) -> bool:
        """Check if currently listening"""
        return self.is_running
