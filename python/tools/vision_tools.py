#!/usr/bin/env python3
"""
Vision Tools using Gemini 1.5 Flash
Allows Jarvis to 'see' the screen.
"""

import os
import subprocess
import tempfile
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# Load env from parent of parent (jarvis/python/.env)
load_dotenv(Path(__file__).parent.parent.parent / ".env")

GEMINI_KEYS = [k for k in [
    os.getenv("GEMINI_API_KEY_1", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
] if k]

def _get_gemini_model():
    """Get configured Gemini model"""
    if not GEMINI_KEYS:
        return None
        
    try:
        import google.generativeai as genai
    except ImportError:
        print("⚠️ google-generativeai not installed")
        return None
    
    # Simple rotation: just use the first working one
    for key in GEMINI_KEYS:
        try:
            genai.configure(api_key=key)
            return genai.GenerativeModel('gemini-1.5-flash')
        except:
            continue
    return None

def capture_screen_to_temp() -> Optional[str]:
    """Capture screen to a temporary file and return path"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            temp_path = f.name
            
        # MacOS screencapture
        # -x: no sound
        # -C: capture cursor
        subprocess.run(["screencapture", "-x", "-C", temp_path], check=True)
        
        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
            return temp_path
        return None
    except Exception as e:
        print(f"Screenshot error: {e}")
        return None

def analyze_screen(query: str = "Describe what is on the screen") -> str:
    """
    Take a screenshot and analyze it using Gemini Vision.
    Args:
        query: What to look for or ask about the screen.
    """
    model = _get_gemini_model()
    if not model:
        return "Vision unavailable (Gemini API key missing)."
    
    print("👀 Looking at screen...", end=" ", flush=True)
    
    image_path = capture_screen_to_temp()
    if not image_path:
        return "Failed to capture screen."
    
    try:
        from PIL import Image
        img = Image.open(image_path)
        
        # Construct prompt
        prompt = f"Analyze this screenshot of my computer screen. {query}. Be concise."
        
        response = model.generate_content([prompt, img])
        text = response.text.strip()
        
        print("✓")
        return text
        
    except ImportError:
        return "Pillow (PIL) not installed."
    except Exception as e:
        print(f"✗ ({str(e)[:50]})")
        return f"Vision analysis failed: {e}"
    finally:
        # Cleanup
        if image_path and os.path.exists(image_path):
            try:
                os.unlink(image_path)
            except:
                pass
