import os
from tavily import TavilyClient

tavily_client = None

def init_tavily():
    global tavily_client
    api_key = os.getenv("TAVILY_API_KEY")
    if api_key:
        try:
            tavily_client = TavilyClient(api_key=api_key)
            print("✅ Tavily Client Initialized")
        except Exception as e:
            print(f"⚠️ Tavily Init Failed: {e}")

def tavily_search(query: str):
    """
    Performs a web search using Tavily.
    Use this when Google Search is unavailable or you need a second opinion.
    """
    if not tavily_client:
        return "Tavily API key not configured."
    
    try:
        response = tavily_client.search(query=query, search_depth="basic")
        results = response.get("results", [])
        summary = "\n".join([f"- {r['title']}: {r['content'][:200]}..." for r in results[:3]])
        return summary
    except Exception as e:
        return f"Error searching Tavily: {e}"
