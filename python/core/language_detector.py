#!/usr/bin/env python3
"""
Language Detection for Multi-language Support
"""

import re
from typing import Optional, Tuple


# Language code mappings
LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Chinese",
    "zh-TW": "Taiwanese Mandarin",
    "ja": "Japanese",
    "ko": "Korean",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
}


def detect_language_from_text(text: str) -> str:
    """
    Detect language from text using character pattern analysis.
    Returns ISO 639-1 language code.
    """
    if not text or not text.strip():
        return "en"
    
    text = text.strip()
    
    # Chinese (Simplified and Traditional)
    if any('\u4e00' <= char <= '\u9fff' for char in text):
        # Check for Traditional Chinese markers
        if any(char in text for char in ['繁體', '傳統', '台灣']):
            return "zh-TW"
        return "zh"
    
    # Japanese (Hiragana/Katakana/Kanji)
    if any('\u3040' <= char <= '\u30ff' for char in text) or \
       any('\u3400' <= char <= '\u4dbf' for char in text):
        return "ja"
    
    # Korean (Hangul)
    if any('\uac00' <= char <= '\ud7af' for char in text):
        return "ko"
    
    # Arabic
    if any('\u0600' <= char <= '\u06ff' for char in text):
        return "ar"
    
    # Russian/Cyrillic
    if any('\u0400' <= char <= '\u04ff' for char in text):
        return "ru"
    
    # Spanish indicators - require stronger signals
    spanish_patterns = [
        r'\b(hola|adiós|gracias|por favor|buenos días|buenas tardes)\b',
        r'\b(cómo estás|qué tal|dónde está|cuándo es|por qué)\b',
        r'\b(me gusta|te gusta|le gusta|nos gusta|les gusta)\b',
    ]
    spanish_matches = sum(1 for pattern in spanish_patterns if re.search(pattern, text, re.IGNORECASE))
    if spanish_matches >= 2:
        return "es"
    
    # French indicators - require stronger signals
    french_patterns = [
        r'\b(bonjour|au revoir|merci beaucoup|s\'il vous plaît|comment allez-vous)\b',
        r'\b(comment ça va|qu\'est-ce que|où est|quand est|pourquoi est)\b',
        r'\b(je suis|tu es|il est|elle est|nous sommes|vous êtes|ils sont)\b',
    ]
    french_matches = sum(1 for pattern in french_patterns if re.search(pattern, text, re.IGNORECASE))
    if french_matches >= 2:
        return "fr"
    
    # German indicators - be more strict to avoid false positives
    # Need multiple German words or German-specific grammar
    german_patterns = [
        r'\b(hallo|auf wiedersehen|danke schön|bitte schön|guten tag|guten morgen)\b',
        r'\b(wie geht|was ist|wo ist|wann ist|warum ist)\b',
        r'\b(ich bin|du bist|er ist|sie ist|wir sind|ihr seid)\b',
        r'\b(der|die|das)\s+\w+',  # German articles with noun
    ]
    # Require at least 2 German indicators or one strong indicator
    german_matches = sum(1 for pattern in german_patterns if re.search(pattern, text, re.IGNORECASE))
    if german_matches >= 2:
        return "de"
    
    # Italian indicators
    italian_patterns = [
        r'\b(ciao|arrivederci|grazie|per favore|sì|no)\b',
        r'\b(come|cosa|dove|quando|perché)\b'
    ]
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in italian_patterns):
        return "it"
    
    # Portuguese indicators
    portuguese_patterns = [
        r'\b(olá|tchau|obrigado|por favor|sim|não)\b',
        r'\b(como|o que|onde|quando|por quê)\b'
    ]
    if any(re.search(pattern, text, re.IGNORECASE) for pattern in portuguese_patterns):
        return "pt"
    
    # Hindi indicators (basic)
    if any('\u0900' <= char <= '\u097f' for char in text):
        return "hi"
    
    # Default to English
    return "en"


def get_language_name(lang_code: str) -> str:
    """Get language name from code"""
    return LANGUAGE_NAMES.get(lang_code, "Unknown")


def parse_language_command(text: str) -> Optional[str]:
    """
    Parse explicit language commands like "speak in Spanish" or "respond in Chinese".
    Returns language code if found, None otherwise.
    """
    text_lower = text.lower().strip()
    
    # Map language names to codes
    language_map = {
        "english": "en", "chinese": "zh", "mandarin": "zh",
        "japanese": "ja", "korean": "ko", "spanish": "es",
        "french": "fr", "german": "de", "italian": "it",
        "portuguese": "pt", "russian": "ru", "arabic": "ar",
        "hindi": "hi", "taiwanese": "zh-TW"
    }
    
    # Check for patterns like "speak in X", "respond in X", "use X"
    patterns = [
        r'speak in (\w+)',
        r'respond in (\w+)',
        r'use (\w+)',
        r'in (\w+)',
        r'speak (\w+)',
        r'talk in (\w+)',
        r'language.*?(\w+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            lang_name = match.group(1)
            if lang_name in language_map:
                return language_map[lang_name]
    
    return None


def detect_language(text: str, conversation_history: Optional[list] = None) -> Tuple[str, bool]:
    """
    Detect language from text, considering conversation history.
    Returns (language_code, is_explicit_command)
    """
    # First check for explicit language commands
    explicit_lang = parse_language_command(text)
    if explicit_lang:
        return explicit_lang, True
    
    # Check conversation history for language consistency
    if conversation_history:
        recent_messages = conversation_history[-5:]  # Last 5 messages
        languages = [detect_language_from_text(msg.get('content', '')) for msg in recent_messages]
        if languages:
            # Use most common recent language
            from collections import Counter
            lang_counts = Counter(languages)
            most_common = lang_counts.most_common(1)[0][0]
            if lang_counts[most_common] >= 2:  # At least 2 messages in same language
                current_lang = detect_language_from_text(text)
                # If current message matches recent language, use it
                if current_lang == most_common or current_lang == "en":
                    return most_common, False
    
    # Detect from current text
    return detect_language_from_text(text), False
