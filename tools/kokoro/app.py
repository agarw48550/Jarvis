import os
import io
import wave
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response
from kokoro_onnx import Kokoro

DEFAULT_VOICES_BIN = os.path.join(os.path.dirname(__file__), 'voices', 'voices.bin')
MODELS = {}

def resolve_voice_id(voice: str) -> str:
    # Accept aliases like 'daniel' and expand to full id
    if '/' not in voice:
        alias = voice.strip().lower()
        # Map friendly names to available styles in voices.bin
        return {
            'daniel': 'am_michael',  # Approximate male voice
            'ryan': 'am_adam',
            'amy': 'af_nicole',
            'michael': 'am_michael',
        }.get(alias, voice)
    return voice

def get_model(model_key: str) -> Kokoro:
    if model_key not in MODELS:
        # Kokoro requires the base model (kokoro-v*.onnx) and a voices dir with embeddings
        # Prefer explicit env paths when provided
        model_env = os.getenv('KOKORO_MODEL_PATH')
        voices_env = os.getenv('KOKORO_VOICES_PATH')

        base_model = None
        if model_env and os.path.isfile(model_env):
            base_model = model_env
        else:
            # Pick best-available base model if present; default path under tools/kokoro/models
            models_dir = os.path.join(os.path.dirname(__file__), 'models')
            candidates = [
                os.path.join(models_dir, 'kokoro-v1.0.onnx'),
                os.path.join(models_dir, 'kokoro-v0_19.onnx'),
            ]
            base_model = next((p for p in candidates if os.path.isfile(p)), None)
        if not base_model:
            raise FileNotFoundError("Kokoro base model not found (expected in tools/kokoro/models).")
        voices_path = voices_env if voices_env else DEFAULT_VOICES_BIN
        MODELS[model_key] = Kokoro(model_path=base_model, voices_path=voices_path)
    return MODELS[model_key]

app = FastAPI()

class SynthesizeRequest(BaseModel):
    text: str
    voice: str
    speed: float | None = 1.0

@app.get("/health")
async def health():
    """Basic health check: verifies model/voices availability."""
    try:
        _ = get_model('default')
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
    try:
        voice_id = resolve_voice_id(req.voice)
        # The Kokoro voices are referenced by style name within voices.bin; here we pass the voice id
        # directly. Use Kokoro's native speed control to avoid artifacts.
        tts = get_model('default')
        speed = float(req.speed or 1.0)
        audio, sr = tts.create(req.text, voice=voice_id, speed=speed)
        # Normalize to wav 16-bit
        sr = int(sr or 22050)
        pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype('<i2')
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sr)
            w.writeframes(pcm16.tobytes())
        return Response(content=buf.getvalue(), media_type="audio/wav")
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
