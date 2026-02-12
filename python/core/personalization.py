import asyncio
import json
import logging
import traceback
from core.memory import init_database, add_fact, get_all_facts, update_conversation_summary, get_current_conversation_id
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
        if not conversation_text or len(conversation_text) < 20:
            return

        prompt = f"""
        Act as a proactive personal observer. Analyze the following conversation between a User and Jarvis.
        Your goal is to extract SUBTLE personality traits, preferences, habits, life updates, and recurring themes that reveal who the user is.
        
        DON'T just look for explicit commands like "remember this". Look for clues in their speech:
        - Preferences: (e.g., "I hate long emails", "I love dark mode", "I usually drink coffee in the morning")
        - Habits/Routine: (e.g., "I'm going to the gym now", "I have a meeting every Tuesday")
        - Life Context: (e.g., "My daughter is starting school", "I'm working on a project about RAG")
        - Emotional Tone: (e.g., "User sounds stressed about work", "User is very tech-savvy")
        
        Transcript:
        {conversation_text}
        
        Output strictly in JSON format:
        {{
            "facts": [
                {{"fact": "User prefers concise technical explanations", "category": "preferences"}},
                {{"fact": "User has a recurring weekly meeting on Tuesdays", "category": "routine"}},
                {{"fact": "User is currently developing a RAG-based memory system", "category": "projects"}}
            ],
            "summary": "1-2 sentence summary of the current state of conversation for immediate session resumption"
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
                    fact_text = item["fact"]
                    if add_fact(fact_text, item.get("category", "general")):
                        print(f"🧠 [PROACTIVE MEMORY] Jarvis learned: \"{fact_text}\"")
                    
            # Save summary to conversation record
            if summary:
                conv_id = get_current_conversation_id()
                update_conversation_summary(conv_id, summary)
                print(f"📝 Session summary saved: {summary}")
            
        except Exception as e:
            print(f"Personalization Failed: {e}")
            traceback.print_exc()

# Singleton
personalization = PersonalizationEngine()
