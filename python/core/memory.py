#!/usr/bin/env python3
"""
Enhanced Memory System with SQLite
Supports vector embeddings for RAG (when sqlite-vec is available)
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
import sys

# Database path
DB_DIR = Path(__file__).parent.parent / "data"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "jarvis.db"

# Embedding model (lazy loaded)
_embedding_model = None

def get_embedding_model():
    """Lazy load embedding model"""
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use lightweight multilingual model
            _embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            print("✅ Embedding model loaded")
        except ImportError:
            print("⚠️ sentence-transformers not installed, vector search disabled")
            _embedding_model = False
        except Exception as e:
            print(f"⚠️ Could not load embedding model: {e}")
            _embedding_model = False
    return _embedding_model if _embedding_model else None


def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Conversations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            ended_at DATETIME,
            message_count INTEGER DEFAULT 0,
            summary TEXT
        )
    """)
    
    # Messages table (conversation history)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            embedding BLOB,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    """)
    
    # Facts table (user facts)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            embedding BLOB,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Context cache (for RAG)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS context_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_hash TEXT UNIQUE,
            context TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # User preferences table (voice, humor, style, etc.)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)")
    
    conn.commit()
    conn.close()


def get_current_conversation_id() -> int:
    """Get or create current conversation ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get most recent active conversation (no end date)
    cursor.execute("""
        SELECT id FROM conversations 
        WHERE ended_at IS NULL 
        ORDER BY started_at DESC 
        LIMIT 1
    """)
    
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]
    
    # Create new conversation
    cursor.execute("INSERT INTO conversations (started_at) VALUES (CURRENT_TIMESTAMP)")
    conn.commit()
    conv_id = cursor.lastrowid
    conn.close()
    return conv_id


def text_to_embedding(text: str) -> Optional[bytes]:
    """Convert text to embedding vector"""
    model = get_embedding_model()
    if not model:
        return None
    
    try:
        embedding = model.encode(text)
        return embedding.tobytes()
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return None


def cosine_similarity(emb1: bytes, emb2: bytes) -> float:
    """Calculate cosine similarity between two embeddings"""
    try:
        import numpy as np
        vec1 = np.frombuffer(emb1, dtype=np.float32)
        vec2 = np.frombuffer(emb2, dtype=np.float32)
        dot = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)
    except:
        return 0.0


# ============== Public API ==============

def add_message(role: str, content: str, conversation_id: Optional[int] = None) -> int:
    """Add a message to conversation history"""
    init_database()
    
    if conversation_id is None:
        conversation_id = get_current_conversation_id()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Generate embedding if model available
    embedding = text_to_embedding(content)
    
    cursor.execute("""
        INSERT INTO messages (conversation_id, role, content, embedding)
        VALUES (?, ?, ?, ?)
    """, (conversation_id, role, content, embedding))
    
    # Update conversation message count
    cursor.execute("""
        UPDATE conversations 
        SET message_count = message_count + 1 
        WHERE id = ?
    """, (conversation_id,))
    
    message_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return message_id


def get_relevant_context(user_message: str, limit: int = 5) -> str:
    """
    Get relevant context from past conversations using RAG.
    Returns formatted context string.
    """
    init_database()
    
    # Try vector search if embeddings available
    user_embedding = text_to_embedding(user_message)
    
    if user_embedding:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get all messages with embeddings
            cursor.execute("""
                SELECT content, embedding, timestamp 
                FROM messages 
                WHERE embedding IS NOT NULL 
                ORDER BY timestamp DESC 
                LIMIT 50
            """)
            
            messages = cursor.fetchall()
            conn.close()
            
            # Calculate similarities
            similarities = []
            for content, emb_bytes, timestamp in messages:
                if emb_bytes:
                    sim = cosine_similarity(user_embedding, emb_bytes)
                    similarities.append((sim, content, timestamp))
            
            # Sort by similarity and take top N
            similarities.sort(reverse=True, key=lambda x: x[0])
            top_messages = similarities[:limit]
            
            if top_messages:
                context_parts = [f"'{msg[1]}' (from {msg[2][:10]})" for msg in top_messages if msg[0] > 0.3]
                if context_parts:
                    return "Relevant context from past conversations:\n" + "\n".join(context_parts)
        
        except Exception as e:
            print(f"⚠️ Vector search error: {e}")
    
    # Fallback: Get recent messages
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content FROM messages 
            WHERE role = 'assistant' 
            ORDER BY timestamp DESC 
            LIMIT ?
        """, (limit,))
        recent = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if recent:
            return "Recent conversation context:\n" + "\n".join([f"- {msg}" for msg in recent])
    except Exception as e:
        print(f"⚠️ Context retrieval error: {e}")
    
    return ""


def add_fact(fact: str, category: str = "general") -> bool:
    """Add a fact to memory"""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if fact already exists
    cursor.execute("SELECT id FROM facts WHERE LOWER(fact) = LOWER(?)", (fact,))
    if cursor.fetchone():
        conn.close()
        return False
    
    # Generate embedding
    embedding = text_to_embedding(fact)
    
    cursor.execute("""
        INSERT INTO facts (fact, category, embedding)
        VALUES (?, ?, ?)
    """, (fact, category, embedding))
    
    conn.commit()
    conn.close()
    print(f"💾 Saved to memory: {fact}")
    return True


def get_all_facts() -> List[Dict]:
    """Get all stored facts"""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT fact, category, created_at FROM facts ORDER BY created_at DESC")
    
    facts = []
    for row in cursor.fetchall():
        facts.append({
            "fact": row[0],
            "category": row[1],
            "added_at": row[2]
        })
    
    conn.close()
    return facts


def get_facts_for_prompt() -> str:
    """Get facts formatted for system prompt"""
    facts = get_all_facts()
    if not facts:
        return "I don't have any saved information about the user yet."
    
    return "Things I know about the user:\n" + "\n".join(
        f"- {f['fact']}" for f in facts
    )


def search_facts(query: str, limit: int = 5) -> List[Dict]:
    """Search facts using semantic similarity"""
    init_database()
    
    query_embedding = text_to_embedding(query)
    if not query_embedding:
        # Fallback to keyword search
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fact, category FROM facts 
            WHERE fact LIKE ? 
            LIMIT ?
        """, (f"%{query}%", limit))
        results = [{"fact": row[0], "category": row[1]} for row in cursor.fetchall()]
        conn.close()
        return results
    
    # Vector search
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT fact, category, embedding FROM facts WHERE embedding IS NOT NULL")
        
        facts_with_sim = []
        for fact, category, emb_bytes in cursor.fetchall():
            if emb_bytes:
                sim = cosine_similarity(query_embedding, emb_bytes)
                facts_with_sim.append((sim, {"fact": fact, "category": category}))
        
        conn.close()
        
        facts_with_sim.sort(reverse=True, key=lambda x: x[0])
        return [f[1] for f in facts_with_sim[:limit] if f[0] > 0.3]
    
    except Exception as e:
        print(f"⚠️ Fact search error: {e}")
        return []


def clear_memory():
    """Clear all memory (conversations and facts)"""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    cursor.execute("DELETE FROM conversations")
    cursor.execute("DELETE FROM facts")
    conn.commit()
    conn.close()
    print("🗑️ Memory cleared")


def get_preferences() -> dict:
    """Get user preferences for voice, humor, style, etc."""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM preferences")
    
    prefs = {}
    for row in cursor.fetchall():
        prefs[row[0]] = row[1]
    
    conn.close()
    return prefs


def set_preference(key: str, value: str):
    """Set a user preference"""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO preferences (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(key) DO UPDATE SET
            value = excluded.value,
            updated_at = CURRENT_TIMESTAMP
    """, (key, value))
    conn.commit()
    conn.close()


def get_preference(key: str) -> Optional[str]:
    """Get a single user preference by key"""
    init_database()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM preferences WHERE key = ?", (key,))
    row = cursor.fetchone()
    conn.close()
    
    return row[0] if row else None


def get_preferences_for_prompt() -> str:
    """Get preferences formatted for system prompt"""
    prefs = get_preferences()
    if not prefs:
        return ""
    
    lines = []
    if "voice_style" in prefs:
        lines.append(f"Preferred voice style: {prefs['voice_style']}")
    if "humor_level" in prefs:
        lines.append(f"Humor level: {prefs['humor_level']}")
    if "conversation_style" in prefs:
        lines.append(f"Conversation style: {prefs['conversation_style']}")
    if "formality" in prefs:
        lines.append(f"Formality level: {prefs['formality']}")
    if "response_length" in prefs:
        lines.append(f"Preferred response length: {prefs['response_length']}")
    
    if lines:
        return "User preferences:\n" + "\n".join(f"- {line}" for line in lines)
    return ""


# Backwards compatibility with old JSON-based memory
def load_memory() -> dict:
    """Backwards compatibility - returns dict format"""
    facts = get_all_facts()
    return {"facts": facts, "conversation_count": len(get_all_facts())}


def save_memory(memory: dict):
    """Backwards compatibility - save from dict format"""
    if "facts" in memory:
        for fact_data in memory.get("facts", []):
            if isinstance(fact_data, dict):
                add_fact(fact_data.get("fact", ""), fact_data.get("category", "general"))
            elif isinstance(fact_data, str):
                add_fact(fact_data)


# Initialize database on import
try:
    init_database()
except Exception as e:
    print(f"⚠️ Database initialization error: {e}")
