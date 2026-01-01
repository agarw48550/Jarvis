from .tavily_search import init_tavily, tavily_search
from .external_llms import init_external_llms, ask_groq, ask_cerebras

def init_all_tools():
    init_tavily()
    init_external_llms()
