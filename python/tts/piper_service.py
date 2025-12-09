#!/usr/bin/env python3
"""Text-to-Speech using Piper TTS"""

import os
import tempfile
import subprocess
import platform
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
VOICES_DIR = BASE_DIR / 'assets' / 'voices'

VOICE_MODELS = {
    'male': {
        'model':  VOICES_DIR / 'male' / 'en_US-ryan-high.onnx',
        'config': VOICES_DIR / 'male' / 'en_US-ryan-high.onnx.json'
    },
    'female': {
        'model':  VOICES_DIR / 'female' / 'en_US-amy-medium.onnx',
        'config':  VOICES_DIR / 'female' / 'en_US-amy-medium.onnx.json'
    }
}

def text_to_speech(text: str, voice: str = 'male') -> str:
    """
    Convert text to speech audio file.
    
    Args:
        text: Text to speak
        voice: 'male' or 'female'
        
    Returns: 
        Path to generated WAV file
    """
    voice_config = VOICE_MODELS.get(voice, VOICE_MODELS['male'])
    model_path = voice_config['model']
    
    if not model_path.exists():
        raise FileNotFoundError(
            f"Voice model not found: {model_path}\n"
            f"Please download voice packs first."
        )
    
    # Create temp output file
    output_file = tempfile.NamedTemporaryFile(
        suffix='.wav',
        delete=False,
        prefix='jarvis_tts_'
    )
    output_path = output_file.name
    output_file.close()
    
    try:
        # Try using piper-tts Python package
        from piper import PiperVoice
        
        voice_model = PiperVoice.load(str(model_path))
        
        with open(output_path, 'wb') as f:
            voice_model.synthesize(text, f)
        
        return output_path
        
    except ImportError:
        # Fallback:  Use piper CLI
        try: 
            cmd = [
                'piper',
                '--model', str(model_path),
                '--output_file', output_path
            ]
            
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            process.communicate(input=text.encode('utf-8'))
            
            if process.returncode != 0:
                raise RuntimeError("Piper CLI failed")
            
            return output_path
            
        except FileNotFoundError: 
            raise RuntimeError(
                "Piper TTS not installed. Install with: pip install piper-tts"
            )

def play_audio(audio_path: str):
    """Play audio file using system default player"""
    if not os.path.exists(audio_path):
        print(f"Audio file not found: {audio_path}")
        return
    
    system = platform.system()
    
    try:
        if system == 'Darwin':  # macOS
            subprocess.run(['afplay', audio_path], check=True)
        elif system == 'Windows':
            # Use PowerShell for better compatibility
            subprocess.run([
                'powershell', '-c',
                f'(New-Object Media.SoundPlayer "{audio_path}").PlaySync()'
            ], check=True)
        else:  # Linux
            # Try multiple players
            for player in ['aplay', 'paplay', 'mpv', 'ffplay']:
                try:
                    if player == 'ffplay':
                        subprocess.run([player, '-nodisp', '-autoexit', audio_path], 
                                      check=True, capture_output=True)
                    else: 
                        subprocess.run([player, audio_path], check=True, capture_output=True)
                    break
                except FileNotFoundError: 
                    continue
    except Exception as e:
        print(f"Could not play audio: {e}")
