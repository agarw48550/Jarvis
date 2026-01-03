import asyncio
import os
import inspect
from dotenv import load_dotenv
from google import genai
from google.genai.types import LiveConnectConfig

load_dotenv()

async def inspect_session():
    api_key = os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ Error: GEMINI_API_KEY_1 or GEMINI_API_KEY not found in .env")
        return

    print(f"Using API Key: {api_key[:10]}...")
    client = genai.Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
    config = LiveConnectConfig(response_modalities=["AUDIO"])
    
    print("Connecting to v1alpha...")
    try:
        async with client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
            print(f"✅ Session Established: {session}")
            print(f"Available attributes: {dir(session)}")
            
            # Check send signature
            if hasattr(session, 'send'):
                sig = inspect.signature(session.send)
                print(f"session.send signature: {sig}")
            else:
                print("session.send attribute not found.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        
if __name__ == "__main__":
    asyncio.run(inspect_session())
