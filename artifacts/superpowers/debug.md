# Debug Report: Session Manager Infinite Retry Loop

## Symptom
User reported "multiple requests" in the API dashboard, followed by audio glitches and application crash.

## Repro Steps
1. Simulate a condition where the Gemini API returns a 409 Conflict, or the connection drops repeatedly.
2. Observe `session_manager.py` logic.
3. The application will enter a tight loop of reconnecting, potentially spawning new threads/audio workers rapidly.

## Root Cause
The `_session_loop` in `session_manager.py` has a nested loop structure:
1. Outer loop: `while self.state["active"]:` (Handles voice changes and sessions).
2. Inner loop: `while attempt < max_retries:` (Handles 409 retries).

**Issue 1**: If the inner loop exhausts retries (reaches `max_retries`), it breaks. The code then falls through to the outer loop. Since `self.state["active"]` is still `True`, it immediately re-initializes the client and restarts the inner loop. This creates an infinite retry loop with no backoff transparency to the user.

**Issue 2**: `attempt` is reset to 0 immediately upon connection entry. If the connection is established but drops (e.g., due to a server-side error or network blip), the code loops back, resets attempts, and retries indefinitely.

## Fix
1.  **Infinite Loop Fix**: Explicitly set `self.state["active"] = False` when max retries are exhausted to stop the outer control loop.
2.  **Concurrency Crash Fix**: Introduced `current_run_active` flag in `_session_loop`.
    - This flag is passed to the `playback_worker` lambda (e.g., `lambda: current_run_active and self.state["active"]`).
    - The flag is set to `False` during cleanup *before* cancelling tasks. This ensures that the zombie worker thread from a previous failed connection stops writing to the `PyAudio` stream before a new worker starts, preventing `Trace Trap` (signal 5).

## Regression Protection
- The code uses `asyncio.TaskGroup` logic (implicitly via `run_in_executor` management) to ensure cleaner thread lifecycles.

## Verification
- Ran `test_session_repro.py`.
- **Before Fix**: Script crashed with `Exit code: 133` (Trace Trap) and showed multiple `CONNECTING` states indicating rapid retries.
- **After Fix**: Script completed successfully with `Exit code: 0`. Audio playback tasks cleaned up correctly without segfaults.
