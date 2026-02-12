"""
Cross-Context Synthesis Module
Part of the "Elephant" Protocol.
Synthesizes information from multiple sources (Calendar, Notes, Memory) to provide holistic insights.
"""

from typing import List, Dict
import concurrent.futures
from core.memory import retrieve_relevant_context

def synthesize_info(query: str, tools_registry: Dict) -> str:
    """
    Gather info from various sources and synthesize it.
    Args:
        query: User's question (e.g., "Prepare for my meeting tomorrow")
        tools_registry: Dictionary of available tools to call (calendar, notes, etc.)
    """
    
    # 1. Identify relevant sources based on keywords
    sources_to_check = []
    q_lower = query.lower()
    
    if any(k in q_lower for k in ["meeting", "schedule", "calendar", "appointment"]):
        sources_to_check.append("get_calendar_events")
    
    if any(k in q_lower for k in ["file", "note", "document", "read"]):
        sources_to_check.append("search_files") # Hypothetical tool or use `list_dir`
        
    # Always check memory
    sources_to_check.append("memory")

    results = []

    # 2. Parallel Execution
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {}
        
        # Memory Search
        futures[executor.submit(retrieve_relevant_context, query, limit=3)] = "Memory"
        
        # Tool Calls (Simulated for now, would need actual tool args construction)
        if "get_calendar_events" in sources_to_check and "get_calendar_events" in tools_registry:
             # Basic check for next 2 days
             func = tools_registry["get_calendar_events"]["function"]
             start_arg = {"days": 2} # default
             futures[executor.submit(func, **start_arg)] = "Calendar"

        # Collect results
        for future in concurrent.futures.as_completed(futures):
            source = futures[future]
            try:
                data = future.result()
                if data and "No events" not in str(data):
                    results.append(f"[{source}]: {data}")
            except Exception as e:
                print(f"⚠️ Synthesis error for {source}: {e}")

    if not results:
        return ""

    # 3. Format Synthesis
    return "🧩 CROSS-CONTEXT SYNTHESIS:\n" + "\n".join(results)
