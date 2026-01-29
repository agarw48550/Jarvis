# Superpowers Plan: Jarvis Improvements (Safety, Tools, Personalization)

## Goal
Enhance Jarvis V3 stability and intelligence by implementing:
1.  **Safety Net**: Auto-reset mechanisms for unresponsive sessions (Watchdog).
2.  **Tools**: Expanded toolset (System controls, Weather fallback, etc.).
3.  **Personalization Engine**: Periodic summarization of conversations using Groq/Cerebras to build long-term memory.
4.  **Recall**: Ability for users to query past conversations.

## Assumptions
- User has valid API keys for Groq/Cerebras (or will provide them).
- `sqlite3` is sufficient for local storage (no vector DB requirement for now, though `memory.py` supports it optionally).
- `rumps` (menu bar app) handles threading correctly for the watchdog.

## Plan

### 1. Implement Safety Net (Watchdog)
**Files**: `jarvis/python/core/session_manager.py`
**Change**:
-   Add a `Watchdog` monitoring loop in `_session_loop`.
-   Track `last_activity_time` (audio sent or received).
-   If `time.time() - last_activity_time > 25s` (and in `PROCESSING` state), force reset `self.state["active"] = False` to restart session.
**Verify**:
-   Run `test_session_repro.py` modified to "hang" (not send audio) and verify it resets/exits.

### 2. Implement Personalization Engine
**Files**: `jarvis/python/core/personalization.py` (NEW), `jarvis/python/core/memory.py`
**Change**:
-   Create `PersonalizationEngine` class.
-   Method `summarize_transcript(transcript) -> str`: Uses Groq/Cerebras to extract facts + summary.
-   Method `run_background_learning()`: Runs periodically to process unsaved transcripts from DB.
-   Update `memory.py` to ensure `get_recent_conversations` is efficient.
**Verify**:
-   Run a script `test_personalization.py` that feeds dummy transcript -> checks DB for new "Facts".

### 3. Implement Conversation Recall
**Files**: `jarvis/python/core/memory.py`, `jarvis/python/tools/tool_registry.py`
**Change**:
-   Update `memory.py`: Add `search_conversations(query)` method performing keyword/semantic search on `messages` table.
-   Update `tool_registry.py`: Add `recall_conversation` tool.
**Verify**:
-   Ask Jarvis: "What did we talk about yesterday?" -> Should query DB and summarize.

### 4. Implement New Tools
**Files**: `jarvis/python/tools/system_tools.py`, `jarvis/python/tools/tool_registry.py`
**Change**:
-   Add `get_weather_legacy` (using `wttr.in` as simple fallback if Google fails).
-   Add `list_processes` (top CPU users).
-   Register them in `tool_registry.py`.
**Verify**:
-   Jarvis command: "Check usage" -> returns process list.

## Risks & mitigations
-   **Risk**: Watchdog resets while user is thinking (long silence).
    -   *Mitigation*: Only trigger watchdog if state is `PROCESSING` (waiting for AI), not `LISTENING`.
-   **Risk**: Personalization leaks private info to cloud.
    -   *Mitigation*: We use Groq/Cerebras which are external; ensure user is aware, or use local small model if requested (though latency is bad on M2 Air for LLM). Stick to text-only summarization.
-   **Risk**: Database locking.
    -   *Mitigation*: Use short lived cursors and commit immediately.

## Rollback plan
-   If Safety Net causes loops: Disable watchdog flag in `session_manager.py`.
-   If Personalization crashes: Wrap `personalization.py` calls in try/except and disable feature toggle.
