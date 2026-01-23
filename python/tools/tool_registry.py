#!/usr/bin/env python3
"""Central tool registry"""

from tools.system_tools import open_app, set_volume, get_battery, take_screenshot, set_brightness, control_media
from tools.customization_tools import update_ai_behavior
from tools.productivity_tools import get_time, set_timer, add_reminder, get_reminders, clear_reminders
from core.memory import add_fact
from tools.information_tools import get_weather, calculate
from tools.control_tools import control_music, pause_listening, exit_jarvis, stop_speaking
from tools.communication_tools import send_email, read_emails, get_calendar_events, create_calendar_event
from interfaces.voice.tts_handler import set_voice, list_voices
from tools.transport_tools import (
    set_home_location,
    get_home_location_label,
    sg_bus_arrival,
    sg_bus_arrival_near_me,
    find_bus_stop,
    refresh_bus_stops,
)
from tools.dev_tools import write_extension, run_python_script, list_extensions
from tools.vision_tools import analyze_screen
from tools.external_llms import ask_groq, ask_cerebras, init_external_llms
from tools.google_tools import (
    list_drive_files,
    search_drive,
    list_classroom_courses,
    get_classroom_assignments,
    get_contacts,
    get_directions,
    get_places_nearby,
    get_timezone,
)
from tools.google_assistant import control_device
from search_engine import search_news, search_web

# Initialize LLMs
init_external_llms()

# Tool registry
TOOLS = {
    # Communication
    "send_email": {"function": send_email, "description": "Send an email", "parameters": {"to": "email address", "subject": "subject", "body": "content"}},
    "read_emails": {"function": read_emails, "description": "Read recent emails", "parameters": {"count": "number of emails"}},
    "get_calendar_events": {"function": get_calendar_events, "description": "Get upcoming calendar events", "parameters": {"days": "number of days"}},
    "create_calendar_event": {"function": create_calendar_event, "description": "Create a calendar event", "parameters": {"title": "event title"}},
    
    # Information
    "search_news": {"function": search_news, "description": "Get latest news on a topic", "parameters": {"query": "news topic"}},
    "search": {"function": search_web, "description": "Search the web for any topic. Use this when grounding isn't enough or for specific queries.", "parameters": {"query": "search query"}},
    "open_app": {"function": open_app, "description": "Open an application", "parameters": {"app_name": "app name"}},
    "get_time": {"function": get_time, "description": "Get current time", "parameters": {}},
    "set_timer": {"function": set_timer, "description": "Set a timer", "parameters": {"minutes": "number", "label": "name (optional)"}},
    "control_music": {"function": control_media, "description": "Control system media (Music, Spotify, etc.) Playback actions: play, pause, next, previous, toggle", "parameters": {"action": "play/pause/next/previous"}},
    "set_volume": {"function": set_volume, "description": "Set volume", "parameters": {"level": "0-100", "action": "up/down/mute"}},
    "set_brightness": {"function": set_brightness, "description": "Set screen brightness", "parameters": {"level": "0-100"}},
    "get_battery": {"function": get_battery, "description": "Get battery status", "parameters": {}},
    "take_screenshot": {"function": take_screenshot, "description": "Take screenshot", "parameters": {}},
    "analyze_screen": {"function": analyze_screen, "description": "See the screen. Use this when user asks 'what is on my screen' or 'look at this'.", "parameters": {"query": "what to look for (default: Describe screen)"}},
    "get_weather": {"function": get_weather, "description": "Get weather", "parameters": {"city": "city name"}},
    "add_reminder": {"function": add_reminder, "description": "Add reminder", "parameters": {"text": "what to remember"}},
    "get_reminders": {"function": get_reminders, "description": "List reminders", "parameters": {}},
    "clear_reminders": {"function": clear_reminders, "description": "Clear reminders", "parameters": {}},
    "add_fact": {"function": add_fact, "description": "Remember a fact about the user for future conversations", "parameters": {"fact": "fact to remember"}},
    "calculate": {"function": calculate, "description": "Do math", "parameters": {"expression": "math expression"}},
    "set_home_location": {"function": set_home_location, "description": "Save your address/postal code", "parameters": {"query": "address or postal"}},
    "get_home_location": {"function": get_home_location_label, "description": "Show saved location", "parameters": {}},
    "sg_bus_arrival": {"function": sg_bus_arrival, "description": "Check SG bus arrivals at a stop", "parameters": {"stop_code": "BusStopCode (digits only)", "service_no": "optional service number"}},
    "sg_bus_arrival_near_me": {"function": sg_bus_arrival_near_me, "description": "Check buses near your saved location", "parameters": {"max_stops": "number of stops", "radius_m": "search radius meters"}},
    "find_bus_stop": {"function": find_bus_stop, "description": "Find bus stop code by name/road", "parameters": {"query": "location name or road"}},
    "refresh_bus_stops": {"function": refresh_bus_stops, "description": "Refresh LTA bus stop directory", "parameters": {}},
    "pause_listening": {"function": pause_listening, "description": "Pause listening (only when user explicitly says pause/stop/wait)", "parameters": {}},
    "stop_speaking": {"function": stop_speaking, "description": "Stop current speech (user says stop/quiet/shut up)", "parameters": {}},
    "exit_jarvis": {"function": exit_jarvis, "description": "Exit Jarvis (goodbye/bye/quit)", "parameters": {}},
    "change_voice": {"function": set_voice, "description": "Change TTS voice", "parameters": {"voice": "voice name (e.g. aria, guy, brian, calum)"}},
    "list_voices": {"function": list_voices, "description": "List all available TTS voices", "parameters": {}},
    "write_extension": {"function": write_extension, "description": "Write a new Python extension/tool for Jarvis. (Self-Evolution)", "parameters": {"filename": "filename.py", "code": "python source code"}},
    "run_python_script": {"function": run_python_script, "description": "Execute Python code in a sandbox to test logic.", "parameters": {"code": "python code"}},
    "list_extensions": {"function": list_extensions, "description": "List all custom extensions.", "parameters": {}},
    "ask_groq": {"function": ask_groq, "description": "Ask a question to Llama 3 on Groq (ultra-fast).", "parameters": {"prompt": "question", "model": "optional model ID"}},
    "ask_cerebras": {"function": ask_cerebras, "description": "Ask a question to Llama on Cerebras (ultra-fast).", "parameters": {"prompt": "question", "model": "optional model ID"}},
    "update_ai_behavior": {"function": update_ai_behavior, "description": "Update AI personality or behavior style", "parameters": {"style_key": "voice_style/humor_level/formality", "value": "description of new style"}},
    
    # Google Cloud API Tools
    "list_drive_files": {"function": list_drive_files, "description": "List files from Google Drive", "parameters": {"query": "optional search query", "max_results": "number of files"}},
    "search_drive": {"function": search_drive, "description": "Search Google Drive for files", "parameters": {"query": "search query"}},
    "list_classroom_courses": {"function": list_classroom_courses, "description": "List enrolled Google Classroom courses", "parameters": {}},
    "get_classroom_assignments": {"function": get_classroom_assignments, "description": "Get assignments from a Classroom course", "parameters": {"course_id": "course ID", "course_name": "or course name"}},
    "get_contacts": {"function": get_contacts, "description": "Search contacts from Google People", "parameters": {"query": "optional name to search", "max_results": "number of contacts"}},
    "get_directions": {"function": get_directions, "description": "Get directions between two locations", "parameters": {"origin": "starting location", "destination": "ending location", "mode": "driving/walking/transit/bicycling"}},
    "get_places_nearby": {"function": get_places_nearby, "description": "Find nearby places (restaurants, cafes, etc.)", "parameters": {"location": "address or place name", "place_type": "restaurant/cafe/hospital/etc.", "radius": "search radius in meters"}},
    "get_timezone": {"function": get_timezone, "description": "Get timezone for a location", "parameters": {"location": "place name or address", "lat": "latitude", "lon": "longitude"}},
    
    # Google Assistant
    "google_assistant": {"function": control_device, "description": "Control smart home devices via Google Assistant (lights, switches, etc). Input: Full natural language command e.g. 'Turn on the bedroom lights'", "parameters": {"command": "text command"}},
}
