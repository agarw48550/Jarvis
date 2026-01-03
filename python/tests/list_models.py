import google.generativeai as genai
import os
from dotenv import load_dotenv
from pathlib import Path
import sys

load_dotenv(Path(__file__).parent.parent / ".env")

api_key = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
if not api_key:
    # Try reading from path
    with open(Path(__file__).parent.parent.parent / ".env") as f:
        for line in f:
            if "GEMINI_API_KEY_1" in line:
                api_key = line.split("=")[1].strip().strip('"').strip("'")
                break

if not api_key:
    print("Error: No API key found in .env")
    sys.exit(1)

genai.configure(api_key=api_key)

print(f"Listing models for API Key ending in ...{api_key[-4:]}")
try:
    for m in genai.list_models():
        if 'flash' in m.name.lower() or 'audio' in m.name.lower():
            print(f"- {m.name}: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")
