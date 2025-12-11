#!/usr/bin/env python3
"""
Multi-source search engine with fallbacks
Priority: Tavily (AI-optimized) → Wikipedia → Basic web
"""

import os
import re

TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")


def search_tavily(query: str) -> str:
    """Search using Tavily API (1000 free/month, AI-optimized)"""
    if not TAVILY_KEY:
        return None
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_KEY)
        
        response = client.search(
            query=query,
            search_depth="basic",
            max_results=3,
            include_answer=True
        )
        
        # Get the AI-generated answer if available
        if response.get("answer"):
            return response["answer"]
        
        # Otherwise summarize results
        results = response.get("results", [])
        if results:
            summaries = []
            for r in results[:3]:
                title = r.get("title", "")[:40]
                content = r.get("content", "")[:100]
                summaries.append(f"{title}: {content}")
            return " | ".join(summaries)
        
        return None
    except Exception as e:
        print(f"   (Tavily error: {e})")
        return None


def search_wikipedia(query: str) -> str:
    """Search Wikipedia for factual queries"""
    try:
        import wikipediaapi
        wiki = wikipediaapi.Wikipedia('Jarvis/1.0', 'en')
        
        # Clean query for Wikipedia
        search_term = query.replace("what is ", "").replace("who is ", "").replace("?", "").strip()
        
        page = wiki.page(search_term)
        if page.exists():
            # Get first 2 sentences
            summary = page.summary[:500]
            sentences = summary.split(". ")[:2]
            return ". ".join(sentences) + "."
        
        return None
    except Exception as e:
        print(f"   (Wikipedia error: {e})")
        return None


def search_web(query: str) -> str:
    """
    Main search function with multiple fallbacks.
    Returns a clean, speakable summary.
    """
    print(f"   🔍 Searching: {query[:50]}...")
    
    # Try Tavily first (best for AI)
    result = search_tavily(query)
    if result:
        return clean_for_speech(result)
    
    # Try Wikipedia for factual queries
    result = search_wikipedia(query)
    if result:
        return clean_for_speech(result)
    
    # Try DuckDuckGo as final fallback
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
        
        if results:
            summaries = []
            for r in results[:3]:
                title = r.get('title', '')[:40]
                body = r.get('body', '')[:100]
                if title and body:
                    summaries.append(f"{title}: {body}")
            if summaries:
                return clean_for_speech(" | ".join(summaries))
    except:
        pass
    
    return f"I couldn't find information about {query}. Try being more specific."


def search_news(query: str) -> str:
    """Search for news using Tavily or DuckDuckGo"""
    if TAVILY_KEY:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=TAVILY_KEY)
            
            response = client.search(
                query=query + " news",
                search_depth="basic",
                max_results=3,
                topic="news"
            )
            
            results = response.get("results", [])
            if results:
                headlines = [r.get("title", "")[:60] for r in results[:3]]
                return "Top headlines: " + ". ".join(headlines)
        except:
            pass
    
    # Fallback to DuckDuckGo news
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=3))
        
        if results:
            headlines = [r.get('title', '')[:60] for r in results[:3]]
            return "Top headlines: " + ". ".join(headlines)
    except:
        pass
    
    return "No recent news found."


def clean_for_speech(text: str) -> str:
    """Remove URLs, HTML, and other non-speakable content"""
    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'www\.\S+', '', text)
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove special characters
    text = re.sub(r'[#*_~`|]', '', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # Limit length for speech
    if len(text) > 400:
        sentences = text.split(". ")
        text = ". ".join(sentences[:3]) + "."
    
    return text
