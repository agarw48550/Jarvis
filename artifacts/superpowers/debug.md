# Debug Session: Menu App Crash

## Symptom
User reports "breaks as before" when running `restart_jarvis.sh`.
Possible symptoms from history:
- Trace Trap (Exit 133)
- Infinite 409 Conflict loop
- Audio glitches
- Multiple API requests

## Hypotheses
1. **Hidden Logs**: `restart_jarvis.sh` sends output to `/dev/null`, silencing the error. (Action: Fix logging)
2. **Audio Device Conflict**: `WakeWordListener` might not release the mic before `JarvisSession` tries to use it.
3. **Environment Mismatch**: `restart_jarvis.sh` might pick up wrong env vars or paths, though unlikely given it uses absolute paths.

## Investigation Log
- [x] Modified `restart_jarvis.sh` to log to `jarvis_debug.log` (added `-u` for unbuffered output).
- [ ] User Hypotheses: "2 calls being made" -> Could be double execution or infinite retry loop triggering twice.
- [ ] `ps aux` showed no running `jarvis_menu.py`, meaning it crashed or exited after user interaction.
- [ ] Checking for other python processes.

