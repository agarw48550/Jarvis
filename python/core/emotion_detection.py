"""
Emotion Detection & Adaptive Responses
Detect user emotion from text to adjust assistant's tone and urgency
"""

import re
from typing import Dict, Optional
from enum import Enum


class Emotion(Enum):
    """Detected emotional states"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    URGENT = "urgent"
    GRATEFUL = "grateful"


class EmotionDetector:
    """
    Detect user emotion from text to adjust assistant's tone.
    Simple rule-based for MVP - can upgrade to ML model later.
    """
    
    # Emotion pattern definitions
    FRUSTRATED_PATTERNS = [
        r'\b(frustrated|annoying|stupid|useless|terrible|awful|worst)\b',
        r'(why (won\'t|doesn\'t|can\'t)|not working|broken|failed)',
        r'(\!\!+)',  # Multiple exclamation marks
        r'\b(hate|angry|mad)\b',
    ]
    
    HAPPY_PATTERNS = [
        r'\b(great|awesome|perfect|excellent|love|amazing|wonderful)\b',
        r'(😊|😃|😄|🎉|❤️|👍|✨)',
        r'\b(glad|happy)\b',
    ]
    
    CONFUSED_PATTERNS = [
        r'\b(confused|don\'t understand|what do you mean|huh|unclear|lost)\b',
        r'\?{2,}',  # Multiple question marks
        r'\b(how do|what does|which way)\b.*\?',
    ]
    
    URGENT_PATTERNS = [
        r'\b(urgent|asap|hurry|quick|immediately|emergency|now)\b',
        r'\b(critical|important|serious)\b',
        r'(need.*(now|asap|immediately))',
    ]
    
    GRATEFUL_PATTERNS = [
        r'\b(thank you|thanks|appreciate|grateful)\b',
        r'(you\'re (the best|great|awesome|helpful))',
    ]
    
    def detect(self, text: str) -> Emotion:
        """
        Detect primary emotion from user text.
        
        Args:
            text: User input text
        
        Returns:
            Detected emotion
        """
        text_lower = text.lower()
        
        # Check patterns in priority order (urgent > frustrated > confused > grateful > happy)
        # Urgent is highest priority
        if any(re.search(pattern, text_lower) for pattern in self.URGENT_PATTERNS):
            return Emotion.URGENT
        
        # Frustrated (important to detect early)
        if any(re.search(pattern, text_lower) for pattern in self.FRUSTRATED_PATTERNS):
            return Emotion.FRUSTRATED
        
        # Confused
        if any(re.search(pattern, text_lower) for pattern in self.CONFUSED_PATTERNS):
            return Emotion.CONFUSED
        
        # Grateful
        if any(re.search(pattern, text_lower) for pattern in self.GRATEFUL_PATTERNS):
            return Emotion.GRATEFUL
        
        # Happy
        if any(re.search(pattern, text_lower) for pattern in self.HAPPY_PATTERNS):
            return Emotion.HAPPY
        
        return Emotion.NEUTRAL
    
    def get_response_tone(self, emotion: Emotion) -> Dict[str, str]:
        """
        Get suggested response tone based on detected emotion.
        
        Args:
            emotion: Detected emotion
        
        Returns:
            Dictionary with tone guidance
        """
        tones = {
            Emotion.NEUTRAL: {
                "style": "professional",
                "length": "normal",
                "language": "Clear and informative",
                "example_prefix": ""
            },
            Emotion.HAPPY: {
                "style": "friendly",
                "length": "concise",
                "language": "Warm and positive",
                "example_prefix": "Great! "
            },
            Emotion.FRUSTRATED: {
                "style": "empathetic",
                "length": "concise",
                "language": "Calm and solution-focused",
                "example_prefix": "I understand your frustration. Let me help fix this. "
            },
            Emotion.CONFUSED: {
                "style": "patient",
                "length": "detailed",
                "language": "Clear step-by-step explanations",
                "example_prefix": "Let me clarify that. "
            },
            Emotion.URGENT: {
                "style": "direct",
                "length": "very_concise",
                "language": "Action-oriented and immediate",
                "example_prefix": "Right away. "
            },
            Emotion.GRATEFUL: {
                "style": "friendly",
                "length": "brief",
                "language": "Warm acknowledgment",
                "example_prefix": "You're welcome! "
            }
        }
        
        return tones.get(emotion, tones[Emotion.NEUTRAL])
    
    def adapt_system_prompt(self, base_prompt: str, emotion: Emotion) -> str:
        """
        Adapt system prompt based on detected emotion.
        
        Args:
            base_prompt: Original system prompt
            emotion: Detected user emotion
        
        Returns:
            Adapted system prompt
        """
        tone = self.get_response_tone(emotion)
        
        emotion_guidance = {
            Emotion.FRUSTRATED: "The user seems frustrated. Be empathetic, acknowledge their issue, and focus on solutions. Keep responses short and action-oriented.",
            Emotion.CONFUSED: "The user is confused. Provide clear, step-by-step explanations. Use simple language and confirm understanding.",
            Emotion.URGENT: "The user needs immediate help. Be direct and action-focused. Skip pleasantries and get straight to the solution.",
            Emotion.HAPPY: "The user is in a good mood. Match their positive energy but stay focused on being helpful.",
            Emotion.GRATEFUL: "The user is expressing gratitude. Acknowledge briefly and offer continued assistance.",
            Emotion.NEUTRAL: ""
        }
        
        guidance = emotion_guidance.get(emotion, "")
        
        if guidance:
            return f"{base_prompt}\n\n## Current interaction guidance:\n{guidance}"
        
        return base_prompt


# Usage example
def enhance_response_with_emotion(
    user_input: str,
    base_response: str,
    detector: Optional[EmotionDetector] = None
) -> str:
    """
    Enhance response based on detected emotion.
    
    Args:
        user_input: What the user said
        base_response: Base assistant response
        detector: EmotionDetector instance (creates new if None)
    
    Returns:
        Enhanced response with appropriate tone
    """
    if detector is None:
        detector = EmotionDetector()
    
    emotion = detector.detect(user_input)
    tone = detector.get_response_tone(emotion)
    
    # Add prefix if suggested
    if tone["example_prefix"] and not base_response.startswith(tone["example_prefix"]):
        return tone["example_prefix"] + base_response
    
    return base_response
