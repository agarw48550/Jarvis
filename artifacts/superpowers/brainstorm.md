# Superpowers Brainstorm

## Goal
Enhance Jarvis V3 with a robust safety net for reliability, expand its tool capabilities, and implement a "Self-Evolving" Personalization Engine that uses secondary efficient LLMs (Groq/Cerebras) to summarize conversations and update user context indefinitely.

## Constraints
- **Local Execution**: Primary logic runs on Mac.
- **Latency**: Safety checks and personalization integrations must not degrade real-time voice response latency.
- **Cost/Efficiency**: Use high-speed/low-cost models (Groq Llama-3, Cerebras) for background summarization tasks.
- **Privacy**: All logs and long-term memory must be stored locally (SQLite).

## Known context
- **Current State**: JarvisSession (`session_manager.py`) manages connection but has fragile error handling (just fixed infinite loop).
- **APIs Available**: User has API keys for Gemini, and mentioned accessing Groq/OpenRouter/Cerebras.
- **Database**: `jarvis_data.db` exists.
- **Memory**: Current memory is likely static or simple file-based.
- **Tools**: Tool registry exists but is minimal.

## Risks
- **Race Conditions**: Background summarization updating context while a new session starts.
- **Hallucinations**: Summarizer might corrupt user preferences if not strictly prompted.
- **Safety Net Trigger Happy**: aggressively returning to standby might interrupt long user pauses (thinking time).
- **Context Bloat**: Injecting *too much* information into individual session system prompts might hit token limits or confuse the model.

## Options
### Option 1: Monolithic Upgrade
- Add safety checks inside the main loop.
- Blocking call to summarize after every session.
- **Pros**: Simple to implement.
- **Cons**: Slows down user experience; higher latency between turns or sessions.

### Option 2: Async "Cortex" with Background Workers (Recommended)
- **Safety**: Dedicated "Watchdog" thread that monitors state transitions. If stuck in `PROCESSING` > 15s, force reset.
- **Personalization**:
    - **Session Recorder**: async writes all turns to `conversations` table.
    - **Memory Worker**: Periodically (or post-session) pulls new transcripts -> sends to Groq/Cerebras -> Extracts "Facts" and "Preferences" -> Upserts to `user_context` table.
- **Dynamic Context**: Next session startup queries `user_context` for top K relevant facts (or all if small).

## Recommendation
Implement **Option 2**.
1.  **Safety Net**: Enhance `JarvisSession` with a `Watchdog` class that monitors `last_activity_timestamp` and auto-calls `stop()`/`enter_standby()` on timeout.
2.  **Tools**: Add system control tools (brightness, volume, app management) and information tools (weather, news).
3.  **Personalization Pipeline**:
    -   Create `PersonalizationEngine` class using `Groq` or `Cerebras` SDK.
    -   Implement `summarize_and_learn(transcript)` function.
    -   Integrate into `stop()` sequence as a background thread.
4.  **Conversation Logs**: Expose a simple `view_logs` command or CLI table.

## Acceptance criteria
- [ ] **SafetyNet**: Jarvis automatically returns to standby if it hangs for >20s (configurable).
- [ ] **Tools**: At least 3 new functional tools added and verified.
- [ ] **Memory**: "My favorite color is blue" said in Session A is remembered in Session B without manual config editing.
- [ ] **Architecture**: Session loop remains fast; summarization happens invisible to user.
- [ ] **Logs**: User can see past conversation text in a file or DB viewer.
