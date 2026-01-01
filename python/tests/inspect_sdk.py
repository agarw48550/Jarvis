import asyncio
import os
import inspect
from dotenv import load_dotenv
from google import genai
from google.genai.types import LiveConnectConfig

load_dotenv()

async def inspect_session():
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY_1"), http_options={'api_version': 'v1alpha'})
    config = LiveConnectConfig(response_modalities=["AUDIO"])
    
    print("Connecting...")
    async with client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
        print(f"Session: {session}")
        print(f"Methods: {dir(session)}")
        
        # Check send signature
        sig = inspect.signature(session.send)
        print(f"session.send signature: {sig}")
        
if __name__ == "__main__":
    asyncio.run(inspect_session())
