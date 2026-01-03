import requests
import json
from bytez import Bytez

# Your API Key from Bytez_test
key = "7bddf858a0af0cf38a22cc1c293c944a"

def get_models():
    print("Fetching available models from Bytez...")
    
    # Method 1: Direct API Endpoint (Most reliable)
    try:
        url = "https://api.bytez.com/models/v2/list/models"
        # The documentation suggests 'Key <key>' or just the key in some places, 
        # but 'Key' prefix is standard for their docs.
        headers = {
            "Authorization": f"Key {key}"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            # The API usually returns a list of objects or a dict with an 'output' key
            models = data.get('output') if isinstance(data, dict) and 'output' in data else data
            return models
        else:
            print(f"API request failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"API method failed: {e}")

    # Method 2: Try SDK Inspection (Fallback)
    try:
        print("Attempting SDK method...")
        sdk = Bytez(api_key=key)
        # Check for list.models() structure (common in Bytez SDKs)
        if hasattr(sdk, 'list') and hasattr(sdk.list, 'models'):
            return sdk.list.models()
        # Check for list_models()
        elif hasattr(sdk, 'list_models'):
            return sdk.list_models()
    except Exception as e:
        print(f"SDK method failed: {e}")
    
    return None

models = get_models()

if models:
    print(f"\nSuccessfully retrieved {len(models)} models.")
    print("-" * 50)
    for m in models:
        # Handle different potential response formats
        model_id = None
        if isinstance(m, dict):
            model_id = m.get('modelId') or m.get('id')
            task = m.get('task', 'N/A')
            print(f"• {model_id:<50} (Task: {task})")
        else:
            print(f"• {m}")
    print("-" * 50)
else:
    print("Could not retrieve model list.")