# JARVIS Personalization Features

## Overview
JARVIS now adapts to each user's preferences, communication style, and personality.

## How It Works

### Automatic Learning
The AI observes your communication style and adapts:
- **Formality**: If you're casual, it becomes casual. If you're formal, it stays professional.
- **Humor**: If you use humor, it will use humor back. If you're serious, it stays professional.
- **Response Length**: Adapts to whether you prefer short, direct answers or more detailed ones.
- **Voice Style**: Remembers your preferred voice and uses it.

### Preference Storage
Preferences are stored in the SQLite database and persist across sessions.

## Available Preferences

### Voice Preferences
- `preferred_voice`: Voice name (calum, cillian, atlas, arista)
- Set by saying: "voice calum" or "I prefer the calum voice"

### Communication Style
- `conversation_style`: "casual", "formal", "professional", "relaxed"
- Set automatically based on how you communicate
- Or explicitly: "I prefer a casual style" or "be more formal"

### Humor Level
- `humor_level`: "high", "medium", "low", "none"
- Set automatically if you use humor, or explicitly: "I like humor"

### Response Length
- `response_length`: "short", "medium", "detailed"
- Adapts based on whether you ask detailed questions or prefer quick answers

### Formality
- `formality`: "very formal", "formal", "casual", "very casual"
- Adapts based on your language and communication patterns

## Commands

### View Preferences
- Say: "preferences" or "prefs"
- Shows all your current preferences

### Set Preferences Explicitly
The AI learns preferences from natural conversation:
- "I prefer a casual style" → Sets conversation_style=casual
- "I like humor" → Sets humor_level=high
- "Be more formal" → Sets conversation_style=formal
- "I prefer detailed answers" → Sets response_length=detailed
- "voice calum" → Sets preferred_voice=calum

### View Memory
- Say: "memory"
- Shows all facts and information stored about you

## Examples

**User**: "Hey Jarvis, I prefer a casual, friendly style with lots of humor."
**JARVIS**: Saves preferences and adapts: "Got it! I'll keep things casual and light-hearted. What can I help you with?"

**User**: "Can you be more professional?"
**JARVIS**: Adapts immediately: "Of course. How may I assist you professionally today?"

**User**: Uses casual language and jokes frequently
**JARVIS**: Automatically learns to be more casual and humorous in responses

## Technical Details

Preferences are stored in the `preferences` table in the SQLite database (`data/jarvis.db`).

The system prompt is dynamically updated based on your preferences, ensuring JARVIS adapts its personality and communication style to match yours.



