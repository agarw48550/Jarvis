import asyncio
import json
import logging
import traceback
from core.memory import init_database, add_fact, get_all_facts
from tools.external_llms import ask_groq, ask_cerebras

# Try to use Cerebras first (often faster/higher limits), fallback to Groq
def fast_llm_inference(prompt):
    res = ask_cerebras(prompt)
    if not res or "Error" in res or "not initialized" in res:
        res = ask_groq(prompt)
    return res

class PersonalizationEngine:
    def __init__(self):
        self.running = False
        
    async def summarize_and_learn(self, conversation_text):
        """
        Analyzes a conversation transcript to extract facts and preferences.
        """
        if not conversation_text or len(conversation_text) < 50:
            print("Personalization: Transcript too short to learn from.")
            return

        prompt = f"""
        Analyze the following conversation between a User and Jarvis.
        Extract any new, permanent facts about the user (name, location, preferences, hobbies, relationships).
        Ignore trivial chatter ("Hello", "How are you").
        Ignore facts I likely already know unless changed.
        
        Transcript:
        {conversation_text}
        
        Output strictly in JSON format:
        {{
            "facts": [
                {{"fact": "User is learning Python", "category": "skills"}},
                {{"fact": "User lives in Singapore", "category": "location"}}
            ],
            "summary": "Brief 1-sentence summary of conversation"
        }}
        If nothing worth learning, return facts: [].
        """
        
        try:
            # Run in executor to not block main thread
            response = await asyncio.to_thread(fast_llm_inference, prompt)
            if not response or "Error" in response:
                print(f"Personalization Error: {response}")
                return

            # Clean response (sometimes LLMs add markdown fences)
            clean_res = response.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_res)
            
            facts = data.get("facts", [])
            summary = data.get("summary", "")
            
            print(f"🧠 Learning extracted {len(facts)} new facts.")
            
            # Save facts
            for item in facts:
                if isinstance(item, dict) and "fact" in item:
                    add_fact(item["fact"], item.get("category", "general"))
                    
            # Ideally we'd also update the conversation record with the summary via SQL
            # But 'messages' table is separate. We'll leave it simple for now.
            
        except Exception as e:
            print(f"Personalization Failed: {e}")
            traceback.print_exc()

# Singleton
personalization = PersonalizationEngine()
