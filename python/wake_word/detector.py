import openwakeword
from openwakeword.model import Model
import numpy as np
import threading
import time
from utils.audio import AudioRecorder

class WakeWordDetector:
    def __init__(self, model_names=["hey_jarvis"], on_detected=None):
        # Load models - simple check/download
        try:
            openwakeword.utils.download_models(model_names)
        except:
            pass
            
        self.owwModel = Model(wakeword_models=model_names)
        self.on_detected = on_detected
        self.recorder = None
        self.running = False
        self.thread = None

    def start(self, recorder_instance=None):
        if self.running:
            return

        self.recorder = recorder_instance if recorder_instance else AudioRecorder()
        if not recorder_instance:
             # Only start if we created it
            self.recorder.start()
            
        self.running = True
        self.thread = threading.Thread(target=self._listen)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.recorder and not getattr(self.recorder, 'shared', False):
             # Stop if we own it (simplified logic for now)
             self.recorder.stop()

    def _listen(self):
        print("Wake word detector listening...")
        while self.running:
            # Process audio from recorder
            chunk = self.recorder.get_audio_chunk()
            if chunk:
                # Convert raw bytes to numpy array
                audio = np.frombuffer(chunk, dtype=np.int16)
                
                # Get prediction
                prediction = self.owwModel.predict(audio)
                
                # Check for activation
                for mdl in self.owwModel.prediction_buffer.keys():
                    if prediction[mdl] > 0.5:
                        print(f"Wake word detected: {mdl}")
                        if self.on_detected:
                            self.on_detected()
                        # Debounce/Cooldown could go here
                        self.owwModel.reset()
            else:
                time.sleep(0.01)
