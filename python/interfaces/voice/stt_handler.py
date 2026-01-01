#!/usr/bin/env python3
"""
Speech-to-Text Handler with Groq Whisper API
Fixed version with proper error handling and diagnostics
"""

import os
import subprocess
import tempfile
import requests
import base64
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Heavy dependencies (like faster-whisper) are imported lazily for performance

load_dotenv()

BYTEZ_KEY = os.getenv("BYTEZ_API_KEY", "")
HF_KEY = os.getenv("HF_API_KEY") or os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
DEFAULT_GROQ_STT_MODEL = "whisper-large-v3"
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", DEFAULT_GROQ_STT_MODEL)
GROQ_STT_MODELS: list[str] = []
for candidate in [GROQ_STT_MODEL, "whisper-large-v3", "distil-whisper-large-v3-en"]:
    if candidate and candidate not in GROQ_STT_MODELS:
        GROQ_STT_MODELS.append(candidate)

GROQ_STT_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
ENABLE_LOCAL_STT = os.getenv("ENABLE_LOCAL_STT_FALLBACK", "1").strip().lower() not in {"0", "false", "no"}


def check_dependencies() -> tuple[bool, Optional[str]]:
    """Check if required dependencies are available"""
    # Check sox
    try:
        subprocess.run(["which", "rec"], capture_output=True, check=True, timeout=2)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return False, "sox not installed. Install with: brew install sox"
    
    # Check Groq API key
    if not GROQ_KEY:
        return False, "GROQ_API_KEY not set in .env file"
    
    return True, None


def record_until_silence(max_duration: int = 15, silence_duration: float = 1.5) -> Optional[str]:
    """
    Record audio until silence is detected using sox.
    Returns path to audio file or None if failed.
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_path = temp_file.name
    temp_file.close()
    
    print("🎤 Listening...", end=" ", flush=True)
    
    try:
        # Record with silence detection using sox
        result = subprocess.run([
            "rec", "-q", audio_path,
            "rate", "16k",
            "channels", "1",
            "silence", "1", "0.1", "1%",  # Skip initial silence
            "1", str(silence_duration), "1%",  # Stop after silence
            "trim", "0", str(max_duration)  # Max duration cap
        ], capture_output=True, timeout=max_duration + 5, check=True)
        
        # Check if file has content
        if not os.path.exists(audio_path):
            print("(no file created)")
            return None
            
        file_size = os.path.getsize(audio_path)
        if file_size < 1000:  # Too small, probably just noise
            print("(no speech detected)")
            os.unlink(audio_path)
            return None
            
        print("✓")
        return audio_path
        
    except subprocess.TimeoutExpired:
        print("(timeout)")
        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
            return audio_path
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        return None
    except FileNotFoundError:
        print("\n⚠️ Error: 'sox' command not found.")
        print("   Install with: brew install sox")
        return None
    except subprocess.CalledProcessError as e:
        print(f"(recording error: {e.returncode})")
        if os.path.exists(audio_path):
            os.unlink(audio_path)
        return None
    except Exception as e:
        print(f"\n⚠️ Recording error: {e}")
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass
        return None


def _post_audio_to_groq(audio_path: str, model_name: str, language: Optional[str]):
    with open(audio_path, "rb") as f:
        data = {
            "model": model_name,
            "response_format": "text",
        }
        if language:
            data["language"] = language
        
        return requests.post(
            GROQ_STT_ENDPOINT,
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
            },
            files={"file": (os.path.basename(audio_path), f, "audio/wav")},
            data=data,
            timeout=30
        )


def _format_groq_error(response) -> str:
    if not response:
        return "Unknown error"
    try:
        data = response.json()
        if isinstance(data, dict):
            error_block = data.get("error")
            if isinstance(error_block, dict):
                return error_block.get("message") or error_block.get("code") or response.text
            message = data.get("message")
            if message:
                return str(message)
    except ValueError:
        pass
    return response.text[:120] if response.text else "Unknown error"


def transcribe_groq(audio_path: str, language: Optional[str] = None) -> Optional[str]:
    """
    Transcribe audio using Groq Whisper API with automatic model fallbacks.
    Returns transcribed text or None if failed.
    """
    if not GROQ_KEY:
        print("✗ (No API key)")
        return None
    
    if not os.path.exists(audio_path):
        print("✗ (File not found)")
        return None
    
    print("📝 Transcribing...", end=" ", flush=True)
    
    try:
        last_error = None
        for idx, model_name in enumerate(GROQ_STT_MODELS):
            response = _post_audio_to_groq(audio_path, model_name, language)
            
            if response.status_code == 200:
                text = response.text.strip()
                if text and text != ".":
                    if idx > 0:
                        print(f"(fallback: {model_name}) ", end="")
                    print("✓")
                    return text
                print("(empty)")
                return None
            
            error_msg = _format_groq_error(response)
            last_error = (response.status_code, error_msg, model_name)
            
            if response.status_code == 403 and idx + 1 < len(GROQ_STT_MODELS):
                print(f"\n⚠️ Groq blocked model '{model_name}' ({error_msg}). Trying '{GROQ_STT_MODELS[idx+1]}'...", flush=True)
                continue
            
            break
        
        if last_error:
            status, message, model_name = last_error
            if status == 401:
                print("✗ (Invalid API key)")
            elif status == 429:
                print("✗ (Rate limited)")
            else:
                print(f"✗ (Error {status}: {message})")
        else:
            print("✗ (Unknown error)")
        return None
            
    except requests.exceptions.Timeout:
        print("✗ (Timeout)")
        return None
    except requests.exceptions.ConnectionError:
        print("✗ (Connection error)")
        return None
    except Exception as e:
        print(f"✗ ({str(e)[:50]})")
        return None


def _transcribe_local(audio_path: str) -> Optional[str]:
    """
    Local fallback using faster-whisper (lazy import to avoid heavy startup cost).
    """
    try:
        from stt.whisper_service import transcribe_audio  # type: ignore
    except Exception as exc:
        print(f"\n⚠️ Local Whisper unavailable ({str(exc)[:80]})")
        return None
    
    try:
        print("🧠 Falling back to local Whisper...", end=" ", flush=True)
        text = transcribe_audio(audio_path)
        if text:
            print("✓")
            return text
        print("(empty)")
        return None
    except Exception as exc:
        print(f"\n⚠️ Local Whisper error: {str(exc)[:80]}")
        return None


def _transcribe_bytez(audio_path: str) -> Optional[str]:
    """Transcribe using Bytez (Whisper Large V3 Turbo)"""
    if not BYTEZ_KEY:
        return None

    try:
        from bytez import Bytez
        print("⚡ Transcribing with Bytez...", end=" ", flush=True)
        
        sdk = Bytez(BYTEZ_KEY)
        model = sdk.model("openai/whisper-large-v3-turbo")
        
        with open(audio_path, "rb") as f:
            audio_data = f.read()
            b64_data = base64.b64encode(audio_data).decode("utf-8")
            
        # Format: data:audio/wav;base64,... (assuming wav from rec)
        data_uri = f"data:audio/wav;base64,{b64_data}"
        
        result = model.run(data_uri)
        
        if hasattr(result, 'output') and result.output:
            print("✓")
            return result.output
        
        error = result.error if hasattr(result, 'error') else 'Unknown error'
        print(f"✗ ({error})")
        return None
        
    except ImportError:
        print("✗ (bytez not installed)")
        return None
    except Exception as e:
        print(f"✗ ({str(e)[:50]})")
        return None


def _transcribe_hf(audio_path: str) -> Optional[str]:
    """Transcribe using Hugging Face Inference API (Whisper Large V3 Turbo)"""
    if not HF_KEY:
        return None
        
    try:
        from huggingface_hub import InferenceClient
        print("⚡ Transcribing with HF...", end=" ", flush=True)
        
        client = InferenceClient(provider="auto", api_key=HF_KEY)
        
        # Pass file path directly to handle content-type correctly
        output = client.automatic_speech_recognition(audio_path, model="openai/whisper-large-v3-turbo")
            
        text = output.text if hasattr(output, 'text') else str(output)
        if text:
            print("✓")
            return text
        print("(empty)")
        return None
        
    except ImportError:
        print("✗ (huggingface_hub not installed)")
        return None
    except Exception as e:
        print(f"✗ ({str(e)[:50]})")
        return None


def transcribe_with_fallback(audio_path: str, language: Optional[str] = None) -> Optional[str]:
    """
    Try Hugging Face first (fastest?), then Bytez, then Groq, then optional local Whisper fallback.
    """
    # 1. Try Hugging Face (Requested Optimization)
    text = _transcribe_hf(audio_path)
    if text:
        return text

    # 2. Try Bytez
    text = _transcribe_bytez(audio_path)
    if text:
        return text

    # 3. Try Groq
    text = transcribe_groq(audio_path, language=language)
    if text:
        return text
    
    # 4. Local fallback
    if ENABLE_LOCAL_STT:
        return _transcribe_local(audio_path)
    
    return None


def listen(language_hint: Optional[str] = None) -> Optional[str]:
    """
    Main entry point: Record and transcribe audio.
    Returns transcribed text or None if failed.
    """
    # Check dependencies first
    deps_ok, error_msg = check_dependencies()
    if not deps_ok:
        print(f"⚠️ {error_msg}")
        return None
    
    # Record audio
    audio_path = record_until_silence()
    if not audio_path:
        return None
    
    try:
        # Transcribe
        text = transcribe_with_fallback(audio_path, language=language_hint)
        return text
    finally:
        # Cleanup
        if os.path.exists(audio_path):
            try:
                os.unlink(audio_path)
            except:
                pass


# Backwards compatibility
def transcribe_audio(audio_path: str) -> str:
    """Backwards compatibility wrapper"""
    text = transcribe_groq(audio_path)
    return text if text else ""
