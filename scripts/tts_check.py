import os
import sys
import importlib.util

# Reuse jarvis.speak without starting wake/STT loops
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from jarvis import speak, _prepare_spoken_text


def main():
    text = "This is a test of the Jarvis TTS system."
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    text = _prepare_spoken_text(text)
    print(f"[tts_check] Engine={os.getenv('TTS_ENGINE', 'say')} Text={text}")
    speak(text)


if __name__ == "__main__":
    main()
