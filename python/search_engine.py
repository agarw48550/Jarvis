#!/usr/bin/env python3
"""
Multi-source search engine with fallbacks
Priority: Tavily (AI-optimized) → Wikipedia → Basic web
"""

import hashlib
import os
import re
import time

from pathlib import Path

TAVILY_KEY = os.getenv("TAVILY_API_KEY", "")
CACHE_DIR = Path(__file__).parent / "data"
CACHE_DIR.mkdir(exist_ok=True)
CACHE_FILE = CACHE_DIR / "search_cache.json"
CACHE_TTL = 60 * 15  # 15 minutes


def load_cache():
    if CACHE_FILE.exists():
        try:
            import json
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_cache(cache):
    try:
        import json
        CACHE_FILE.write_text(json.dumps(cache))
    except Exception:
        pass


def read_from_cache(query: str) -> str:
    cache = load_cache()
    key = hashlib.sha256(query.strip().lower().encode()).hexdigest()
    entry = cache.get(key)
    if entry and (time.time() - entry.get("ts", 0)) < CACHE_TTL:
        return entry.get("result")
    return None


def write_cache(query: str, result: str):
    cache = load_cache()
    key = hashlib.sha256(query.strip().lower().encode()).hexdigest()
    cache[key] = {"result": result, "ts": time.time()}
    save_cache(cache)


def search_tavily(query: str) -> str:
    """Search using Tavily API (1000 free/month, AI-optimized)"""
    if not TAVILY_KEY:
        return None
    
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_KEY)
        
        request_kwargs = {
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
            "include_answer": True,
        }

        response = None
        for attempt in range(2):
            try:
                response = client.search(**request_kwargs)
                break
            except Exception:
                if attempt == 0:
                    # Retry with shallower search
                    request_kwargs["search_depth"] = "basic"
                    continue
                raise

        # Get the AI-generated answer if available (best quality)
        if response.get("answer"):
            answer = response["answer"]
            # Clean and summarize if too long
            answer = clean_for_speech(answer)
            if len(answer) > 250:
                sentences = answer.split(". ")
                answer = ". ".join(sentences[:3]) + "."
            return answer
        
        # Otherwise summarize top results with more detail
        results = response.get("results", [])
        if results:
            summaries = []
            for r in results[:3]:
                title = r.get("title", "")[:60]
                content = r.get("content", "")[:120]
                if title:
                    summaries.append(f"{title}" + (f": {content}" if content else ""))
            if summaries:
                return ". ".join(summaries)
        
        # Build summary with sources fallback
        results = response.get("results", [])
        if results:
            summaries = []
            for r in results[:3]:
                title = r.get("title", "")[:60]
                content = r.get("content", "")[:120]
                if title:
                    source = r.get("source", "") or r.get("url", "")
                    source_domain = re.sub(r"https?://(www\.)?", "", source).split("/")[0] if source else ""
                    source_suffix = f" ({source_domain})" if source_domain else ""
                    summaries.append(f"{title}{source_suffix}: {content}")
            if summaries:
                return ". ".join(summaries)
        
        return "No high-quality results from Tavily."
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
    
    cached = read_from_cache(query)
    if cached:
        return cached

    # Try Tavily first (best for AI)
    result = search_tavily(query)
    if result:
        cleaned = clean_for_speech(result)
        write_cache(query, cleaned)
        return cleaned
    
    # Try Wikipedia for factual queries
    result = search_wikipedia(query)
    if result:
        cleaned = clean_for_speech(result)
        write_cache(query, cleaned)
        return cleaned
    
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
                cleaned = clean_for_speech(" | ".join(summaries))
                write_cache(query, cleaned)
                return cleaned
    except:
        pass
    
    final = f"I couldn't find information about {query}. Try being more specific."
    write_cache(query, final)
    return final


def search_news(query: str) -> str:
    """Search for news using Tavily (AI-optimized) or DuckDuckGo"""
    if TAVILY_KEY:
        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=TAVILY_KEY)
            
            # Use include_answer for better AI-formatted responses
            response = client.search(
                query=query + " latest news",
                search_depth="advanced",  # Better quality for news
                max_results=5,
                include_answer=True,
                topic="news"
            )
            
            # Prefer AI-generated answer if available
            if response.get("answer"):
                answer = response["answer"]
                if len(answer) > 300:
                    sentences = answer.split(". ")
                    answer = ". ".join(sentences[:2]) + "."
                return clean_for_speech(answer)
            
            # Otherwise use top headlines with more context
            results = response.get("results", [])
            if results:
                summaries = []
                for r in results[:3]:
                    title = r.get("title", "")[:70]
                    content = r.get("content", "")[:100]
                    if title:
                        summaries.append(f"{title}" + (f": {content}" if content else ""))
                if summaries:
                    return "Latest news: " + ". ".join(summaries[:3])
        except Exception as e:
            print(f"   (Tavily error: {e})")
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
