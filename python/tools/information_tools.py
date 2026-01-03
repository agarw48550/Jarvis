#!/usr/bin/env python3
"""Information tools - Web search, weather, news"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from search_engine import search_web, search_news


def get_weather(city: str = "Singapore") -> str:
    try:
        import urllib.parse
        import requests
        url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        current = data['current_condition'][0]
        temp = current['temp_C']
        desc = current['weatherDesc'][0]['value']
        
        return f"{city}: {temp} degrees Celsius, {desc}."
    except Exception:
        return f"Couldn't get weather for {city}."


def calculate(expression: str) -> str:
    try:
        allowed = set('0123456789+-*/().% ')
        clean = ''.join(c for c in expression if c in allowed)
        result = eval(clean)
        return f"The answer is {result}."
    except Exception:
        return "Couldn't calculate that."
