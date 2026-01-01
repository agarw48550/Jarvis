import os
from groq import Groq
from cerebras.cloud.sdk import Cerebras

groq_client = None
cerebras_client = None

def init_external_llms():
    global groq_client, cerebras_client
    
    # Init Groq
    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        try:
            groq_client = Groq(api_key=groq_key)
            print("✅ Groq Client Initialized")
        except Exception as e:
            print(f"⚠️ Groq Init Failed: {e}")

    # Init Cerebras
    cerebras_key = os.getenv("CEREBRAS_API_KEY")
    if cerebras_key:
        try:
            # Cerebras SDK might auto-read env CEREBRAS_API_KEY
            cerebras_client = Cerebras(api_key=cerebras_key) 
            print("✅ Cerebras Client Initialized")
        except Exception as e:
            print(f"⚠️ Cerebras Init Failed: {e}")

def ask_groq(prompt: str, model: str = "llama3-8b-8192"):
    """
    Asks a question to a fast LLM hosted on Groq (Llama 3).
    Use this for quick logic checks or if specifically asked to "ask llama".
    """
    if not groq_client:
        return "Groq client not initialized."
    
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Error querying Groq: {e}"

def ask_cerebras(prompt: str, model: str = "llama3.1-8b"):
    """
    Asks a question to a fast LLM hosted on Cerebras.
    Use this for alternative fast inference.
    """
    if not cerebras_client:
        return "Cerebras client not initialized."
    
    try:
        completion = cerebras_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error querying Cerebras: {e}"
