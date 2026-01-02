"""
JARVIS Central Configuration
All configuration in one place for easy management
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional, List

load_dotenv()

# ============== Paths ==============
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
BACKUPS_DIR = Path("~/.jarvis/backups").expanduser()

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

# ============== API Keys ==============
@dataclass
class APIKeys:
    gemini_keys: List[str]
    groq_key: Optional[str]
    cerebras_key: Optional[str]
    openrouter_key: Optional[str]
    tavily_key: Optional[str]
    
    @classmethod
    def from_env(cls) -> 'APIKeys': 
        return cls(
            gemini_keys=[k for k in [
                os.getenv("GEMINI_API_KEY_1"),
                os.getenv("GEMINI_API_KEY_2"),
                os.getenv("GEMINI_API_KEY"),
            ] if k],
            groq_key=os.getenv("GROQ_API_KEY"),
            cerebras_key=os.getenv("CEREBRAS_API_KEY"),
            openrouter_key=os.getenv("OPENROUTER_API_KEY"),
            tavily_key=os.getenv("TAVILY_API_KEY"),
        )

API_KEYS = APIKeys.from_env()

# ============== Model Configuration ==============
@dataclass
class ModelConfig:
    # Gemini Live (Voice) - Force latest stable preview for audio
    gemini_live_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"
    gemini_live_api_version: str = "v1beta"
    
    # Gemini Text
    gemini_text_model: str = "gemini-2.0-flash-exp"
    
    # Groq
    groq_model: str = "llama-3.3-70b-versatile"
    groq_whisper_model: str = "whisper-large-v3-turbo"
    
    # Cerebras
    cerebras_model: str = "llama-3.3-70b"
    
    # OpenRouter (free models)
    openrouter_models: List[str] = None
    
    def __post_init__(self):
        if self.openrouter_models is None: 
            self.openrouter_models = [
                "meta-llama/llama-3.3-70b-instruct:free",
                "qwen/qwen3-235b-a22b:free",
            ]

MODELS = ModelConfig()

# ============== Audio Configuration ==============
@dataclass
class AudioConfig:
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000
    chunk_size: int = 1024  # Increased from 512 for better performance
    voice_threshold: float = 0.005  # RMS threshold for voice detection
    default_voice: str = "Puck"  # Gemini voice name

AUDIO = AudioConfig()

# ============== Voice Mappings ==============
VOICE_MAPPINGS = {
    # Male voices
    "male": "Charon",
    "man": "Charon",
    "masculine": "Charon",
    "deeper": "Charon",
    "deep voice": "Charon",
    "charon": "Charon",
    
    # Strong/Bold voices
    "bold": "Fenrir",
    "strong": "Fenrir",
    "powerful": "Fenrir",
    "fenrir": "Fenrir",
    
    # Female voices
    "female": "Aoede",
    "woman": "Aoede",
    "feminine": "Aoede",
    "softer": "Aoede",
    "soft voice": "Aoede",
    "aoede": "Aoede",
    
    # Alternative female
    "gentle": "Kore",
    "kore": "Kore",
    
    # Neutral
    "neutral": "Puck",
    "default": "Puck",
    "puck": "Puck",
}

# ============== Quota Management ==============
@dataclass
class QuotaConfig:
    gemini_daily_limit: int = 40  # 2 accounts × 20 requests
    groq_rpm_limit: int = 30  # Requests per minute
    cerebras_rpm_limit: int = 30

QUOTAS = QuotaConfig()

# ============== Feature Flags ==============
@dataclass
class Features:
    enable_self_evolution: bool = False  # Self-modifying AI (experimental)
    enable_wake_word: bool = True
    enable_web_search: bool = True
    enable_rag_memory: bool = True
    debug_mode: bool = os.getenv("JARVIS_DEBUG", "").lower() == "true"

FEATURES = Features()

# ============== System Prompt ==============
SYSTEM_PROMPT_TEMPLATE = """You are Jarvis, a highly capable AI assistant created for personal use.

PERSONALITY:
- Direct, efficient, and helpful
- Speak concisely - no unnecessary words
- Use natural conversational tone
- Remember context from our entire conversation

CAPABILITIES (use these when appropriate):
- Web Search: For current events, facts, news, weather
- System Control: Volume, brightness, apps, music playback
- Productivity: Calendar, email, reminders, timers
- Memory: Remember user facts and preferences across sessions

VOICE BEHAVIOR:
- Keep responses brief for simple queries (1-2 sentences)
- For complex topics, give summaries first, then offer to elaborate
- Don't repeat back what the user said
- Don't announce tool usage - just use them and report results

WHEN USER ASKS TO CHANGE VOICE:
- "male voice" or "deeper" → Switch to Charon (requires reconnection)
- "female voice" or "softer" → Switch to Aoede (requires reconnection)
- "bold" or "strong" → Switch to Fenrir (requires reconnection)
- "default" or "neutral" → Switch to Puck (requires reconnection)

{user_facts}

{user_preferences}

{recent_context}
"""
