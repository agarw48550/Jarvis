/**
 * SQLite Database Schema and Migrations
 */

export const SCHEMA = `
-- User facts (memory)
CREATE TABLE IF NOT EXISTS user_facts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fact TEXT NOT NULL,
  category TEXT DEFAULT 'general',
  source TEXT DEFAULT 'conversation',
  confidence REAL DEFAULT 1.0,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Conversation sessions
CREATE TABLE IF NOT EXISTS conversations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at DATETIME,
  message_count INTEGER DEFAULT 0,
  summary TEXT
);

-- Individual messages
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  conversation_id INTEGER REFERENCES conversations(id),
  role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  audio_path TEXT,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Action history (audit log)
CREATE TABLE IF NOT EXISTS action_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action_type TEXT NOT NULL,
  parameters TEXT,
  result TEXT,
  success BOOLEAN,
  confirmed_by_user BOOLEAN DEFAULT FALSE,
  executed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User settings
CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Google OAuth tokens (encrypted)
CREATE TABLE IF NOT EXISTS oauth_tokens (
  provider TEXT PRIMARY KEY,
  access_token TEXT,
  refresh_token TEXT,
  expires_at DATETIME,
  scope TEXT,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- User extensions
CREATE TABLE IF NOT EXISTS extensions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  plain_english_explanation TEXT,
  triggers TEXT,
  code TEXT NOT NULL,
  permissions TEXT,
  enabled BOOLEAN DEFAULT TRUE,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_facts_category ON user_facts(category);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_actions_type ON action_history(action_type);
`;

export const DEFAULT_SETTINGS = {
    voice: 'male',
    wake_word: 'hey_jarvis',
    theme: 'dark',
    confirm_dangerous_actions: 'true',
    auto_save_facts: 'true',
    max_conversation_history: '50',
};
