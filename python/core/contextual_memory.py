"""
Contextual Memory & Conversation History
Maintains short-term working memory for natural multi-turn conversations
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import sqlite3
import json
from pathlib import Path

class ConversationalContext:
    """
    Short-term conversational memory (different from long-term facts).
    Tracks conversation turns to maintain context and coherence.
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "memory.db")
        
        self.db_path = db_path
        self.init_context_table()
    
    def init_context_table(self):
        """Create conversation tracking table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversation_context (
                session_id TEXT,
                turn_number INTEGER,
                speaker TEXT,
                utterance TEXT,
                intent TEXT,
                entities TEXT,
                timestamp REAL,
                PRIMARY KEY (session_id, turn_number)
            )
        """)
        conn.commit()
        conn.close()
    
    def add_turn(
        self,
        session_id: str,
        speaker: str,  # "user" or "assistant"
        utterance: str,
        intent: Optional[str] = None,
        entities: Optional[Dict] = None
    ):
        """
        Record a conversation turn.
        
        Args:
            session_id: Unique session identifier
            speaker: Who spoke ("user" or "assistant")
            utterance: What was said
            intent: Optional detected intent
            entities: Optional extracted entities
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get next turn number for this session
        cursor.execute(
            "SELECT MAX(turn_number) FROM conversation_context WHERE session_id = ?",
            (session_id,)
        )
        result = cursor.fetchone()
        turn_number = (result[0] or 0) + 1
        
        # Insert turn
        cursor.execute("""
            INSERT INTO conversation_context
            (session_id, turn_number, speaker, utterance, intent, entities, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            turn_number,
            speaker,
            utterance,
            intent,
            json.dumps(entities) if entities else None,
            datetime.now().timestamp()
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_context(
        self,
        session_id: str,
        num_turns: int = 10
    ) -> List[Dict]:
        """
        Get recent conversation turns for context.
        
        Args:
            session_id: Session to retrieve
            num_turns: Number of recent turns to get
        
        Returns:
            List of conversation turns (chronological order)
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT speaker, utterance, intent, entities, timestamp
            FROM conversation_context
            WHERE session_id = ?
            ORDER BY turn_number DESC
            LIMIT ?
        """, (session_id, num_turns))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to chronological order
        return [
            {
                "speaker": row[0],
                "utterance": row[1],
                "intent": row[2],
                "entities": json.loads(row[3]) if row[3] else None,
                "timestamp": row[4]
            }
            for row in reversed(rows)
        ]
    
    def build_context_prompt(self, session_id: str, num_turns: int = 6) -> str:
        """
        Build a context string to prepend to system prompt.
        
        Args:
            session_id: Session to build context for
            num_turns: Number of recent turns to include
        
        Returns:
            Formatted context string
        """
        recent = self.get_recent_context(session_id, num_turns=num_turns)
        
        if not recent:
            return ""
        
        context_lines = ["## Recent Conversation Context"]
        for turn in recent:
            speaker = "User" if turn["speaker"] == "user" else "Assistant"
            context_lines.append(f"{speaker}: {turn['utterance']}")
        
        return "\n".join(context_lines)
    
    def clear_old_sessions(self, days: int = 7):
        """
        Clear conversation context older than specified days.
        
        Args:
            days: Keep only sessions from the last N days
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).timestamp()
        cursor.execute(
            "DELETE FROM conversation_context WHERE timestamp < ?",
            (cutoff,)
        )
        
        conn.commit()
        conn.close()


class ProactiveAssistant:
    """
    Analyzes user patterns to make proactive suggestions.
    Example: "It's 9 AM - would you like your usual news briefing?"
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_dir = Path(__file__).parent.parent / "data"
            db_dir.mkdir(exist_ok=True)
            db_path = str(db_dir / "memory.db")
        
        self.db_path = db_path
        self.init_patterns_table()
    
    def init_patterns_table(self):
        """Create usage patterns tracking table"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usage_patterns (
                pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_type TEXT,
                day_of_week INTEGER,
                hour_of_day INTEGER,
                frequency INTEGER DEFAULT 1,
                last_occurrence REAL,
                context TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def record_action(self, action_type: str, context: str = ""):
        """
        Record when user performs an action.
        
        Args:
            action_type: Type of action (search_news, get_weather, etc.)
            context: Optional context (e.g., "tech news")
        """
        now = datetime.now()
        day_of_week = now.weekday()  # 0=Monday, 6=Sunday
        hour_of_day = now.hour
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute("""
            SELECT pattern_id, frequency FROM usage_patterns
            WHERE action_type = ? AND day_of_week = ? AND hour_of_day = ?
        """, (action_type, day_of_week, hour_of_day))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing pattern
            pattern_id, freq = result
            cursor.execute("""
                UPDATE usage_patterns
                SET frequency = frequency + 1, 
                    last_occurrence = ?,
                    context = ?
                WHERE pattern_id = ?
            """, (now.timestamp(), context, pattern_id))
        else:
            # Create new pattern
            cursor.execute("""
                INSERT INTO usage_patterns
                (action_type, day_of_week, hour_of_day, last_occurrence, context)
                VALUES (?, ?, ?, ?, ?)
            """, (action_type, day_of_week, hour_of_day, now.timestamp(), context))
        
        conn.commit()
        conn.close()
    
    def get_suggestions(self, min_frequency: int = 3) -> List[str]:
        """
        Get proactive suggestions based on current time and patterns.
        
        Args:
            min_frequency: Minimum occurrences before suggesting
        
        Returns:
            List of suggestion strings
        """
        now = datetime.now()
        day_of_week = now.weekday()
        hour_of_day = now.hour
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Find patterns matching current time with sufficient frequency
        cursor.execute("""
            SELECT action_type, frequency, context
            FROM usage_patterns
            WHERE day_of_week = ? 
            AND hour_of_day = ?
            AND frequency >= ?
            ORDER BY frequency DESC
            LIMIT 3
        """, (day_of_week, hour_of_day, min_frequency))
        
        patterns = cursor.fetchall()
        conn.close()
        
        suggestions = []
        for action_type, freq, context in patterns:
            if action_type == "search_news":
                suggestions.append("Would you like your usual news briefing?")
            elif action_type == "get_weather":
                suggestions.append("Want to check today's weather?")
            elif action_type == "set_timer":
                if context:
                    suggestions.append(f"Time for your usual {context}?")
                else:
                    suggestions.append("Time for your usual timer?")
            elif action_type == "play_music":
                suggestions.append("Ready for some music?")
            else:
                # Generic suggestion for other actions
                suggestions.append(f"You usually do '{action_type}' around this time. Need help with that?")
        
        return suggestions
