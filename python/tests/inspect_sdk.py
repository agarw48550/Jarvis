
import sys
import inspect
from google.genai import types

print(f"Python Version: {sys.version}")
try:
    import google.genai
    print(f"Google GenAI Version: {google.genai.__version__}")
except AttributeError:
    print("Google GenAI version attribute not found.")

print("\n--- LiveConnectConfig Fields ---")
try:
    # Try to inspect the model fields directly if it's a Pydantic model
    for name, field in types.LiveConnectConfig.model_fields.items():
        print(f"- {name}: {field.annotation}")
except Exception as e:
    print(f"Could not inspect model_fields: {e}")
    # Fallback to init inspection
    print("\n--- Init Signature ---")
    print(inspect.signature(types.LiveConnectConfig.__init__))

print("\n--- SpeechConfig Fields ---")
try:
    for name, field in types.SpeechConfig.model_fields.items():
        print(f"- {name}: {field.annotation}")
except Exception:
    pass
