from faster_whisper import WhisperModel
import os

class WhisperService:
    def __init__(self, model_size="tiny", device="cpu", compute_type="int8"):
        model_dir = os.path.join(os.getcwd(), "models")
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
            
        print(f"Loading Whisper model: {model_size} on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type, download_root=model_dir)
        print("Whisper model loaded.")

    def transcribe(self, audio_source, beam_size=5):
        segments, info = self.model.transcribe(audio_source, beam_size=beam_size)
        
        full_text = ""
        for segment in segments:
            full_text += segment.text + " "
            
        return full_text.strip(), info.language
