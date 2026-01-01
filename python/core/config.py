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
    chunk_size: int = 512
    voice_threshold: float = 0.005  # RMS threshold for voice detection
    default_voice: str = "Charon"  # Gemini voice name

AUDIO = AudioConfig()

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
SYSTEM_PROMPT = """You are Jarvis, a helpful, direct, and friendly AI assistant. 

Key behaviors:
- Be concise but helpful
- Use tools when needed (search, calendar, reminders, etc.)
- Maintain conversation context
- Respond in the user's language
- Never output URLs unless specifically asked

Available tools: web search, weather, reminders, calendar, email, system controls, music. 
"""
