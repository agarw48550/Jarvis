import pyaudio
import numpy as np
import threading
import queue

class AudioRecorder:
    def __init__(self, format=pyaudio.paInt16, channels=1, rate=16000, chunk=1280):
        self.format = format
        self.channels = channels
        self.rate = rate
        self.chunk = chunk
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.frames = queue.Queue()
        self.thread = None

    def start(self):
        if self.recording:
            return
        
        self.recording = True
        self.stream = self.audio.open(format=self.format,
                                      channels=self.channels,
                                      rate=self.rate,
                                      input=True,
                                      frames_per_buffer=self.chunk)
        self.thread = threading.Thread(target=self._record)
        self.thread.start()

    def _record(self):
        while self.recording:
            try:
                data = self.stream.read(self.chunk, exception_on_overflow=False)
                self.frames.put(data)
            except Exception as e:
                print(f"Error recording audio: {e}")
                break

    def stop(self):
        self.recording = False
        if self.thread:
            self.thread.join()
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

    def get_audio_chunk(self):
        try:
            return self.frames.get(block=False)
        except queue.Empty:
            return None

    def clear_queue(self):
        with self.frames.mutex:
            self.frames.queue.clear()
            
    def terminate(self):
        self.audio.terminate()
