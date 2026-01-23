# Add Google Cloud API Tools

Add new tools leveraging Google Cloud APIs: Drive, Classroom, Time Zone, Directions, Weather, People, Places, and Workspace Events.

## Assumptions

1. User has already enabled these APIs in Google Cloud Console.
2. OAuth credentials in `.env` (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`) are valid for these APIs.
3. Some APIs (e.g., Weather, Time Zone, Directions, Places) require only an API key, not OAuth.
4. Google Workspace Events API requires admin/domain-wide delegation which may not be available—will implement as a stub or skip if not feasible for personal use.

> [!IMPORTANT]
> After implementation, you must re-run `google_auth.py` to authorize new OAuth scopes (Drive, Classroom, People).

---

## Proposed Changes

### Component: OAuth Configuration

#### [MODIFY] [google_auth.py](file:///Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis%20V3/jarvis/python/google_auth.py)

Add new OAuth scopes for Drive, Classroom, and People APIs:
```python
SCOPES = [
    # Existing
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
    # New
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/classroom.courses.readonly',
    'https://www.googleapis.com/auth/classroom.rosters.readonly',
    'https://www.googleapis.com/auth/contacts.readonly',
]
```

---

### Component: Environment Configuration

#### [MODIFY] [.env](file:///Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis%20V3/jarvis/python/.env)

Add Google Maps API key (required for Directions, Places, Time Zone):
```
GOOGLE_MAPS_API_KEY=<user-provided-key>
```

> [!NOTE]
> Weather API is not a Google service. OpenWeatherMap or similar is recommended. If the user means Google's deprecated Weather API, we'll note it's unavailable.

---

### Component: New Tool Files

#### [NEW] [google_tools.py](file:///Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis%20V3/jarvis/python/tools/google_tools.py)

Create a new file with the following functions:

| Function | API | Description |
|----------|-----|-------------|
| `list_drive_files(query, max_results)` | Drive v3 | List files from Google Drive |
| `search_drive(query)` | Drive v3 | Search Drive for files |
| `list_classroom_courses()` | Classroom v1 | List enrolled courses |
| `get_classroom_assignments(course_id)` | Classroom v1 | Get coursework from a course |
| `get_contacts(query, max_results)` | People v1 | Search contacts |
| `get_directions(origin, destination, mode)` | Directions API | Get directions (driving, walking, transit) |
| `get_places_nearby(location, type, radius)` | Places API | Find nearby places |
| `get_timezone(lat, lon)` | Time Zone API | Get timezone for coordinates |

Each function follows the pattern in `communication_tools.py`:
```python
def get_service(name, version):
    creds = get_credentials()
    if not creds:
        return None
    return build(name, version, credentials=creds)
```

---

### Component: Tool Registry

#### [MODIFY] [tool_registry.py](file:///Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis%20V3/jarvis/python/tools/tool_registry.py)

- Import new functions from `google_tools.py`
- Add entries to the `TOOLS` dictionary

---

## Verification Plan

### Automated Tests

1. **Syntax Check**  
   ```bash
   cd /Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis\ V3/jarvis/python
   python3 -m py_compile tools/google_tools.py google_auth.py tools/tool_registry.py
   ```

2. **Tool Registry Load Test**  
   ```bash
   cd /Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis\ V3/jarvis/python
   python3 tests/test_tool_registry.py
   ```
   Expect: All tools load without errors, callable check passes.

### Manual Verification

After adding `GOOGLE_MAPS_API_KEY` to `.env`:

1. **Re-authenticate OAuth**  
   ```bash
   cd /Users/ayaanagarwal/Documents/Important/Home/Projects/Jarvis\ V3/jarvis/python
   python3 google_auth.py
   ```
   A browser window should open. Authorize the requested scopes.

2. **Test Drive Tool**  
   In Python REPL or a test script:
   ```python
   from tools.google_tools import list_drive_files
   print(list_drive_files())
   ```
   Expect: List of recent Drive files or "No files found."

3. **Test Directions Tool**  
   ```python
   from tools.google_tools import get_directions
   print(get_directions("Singapore Zoo", "Marina Bay Sands", "transit"))
   ```
   Expect: Route summary with duration.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| OAuth token lacks new scopes | Delete `google_token.json` and re-run `google_auth.py` |
| Google Maps API key not set | Gracefully return error message instructing user to add key |
| Rate limits on free tier | Add try/except with informative error messages |
| Workspace Events requires domain admin | Skip implementation or stub with "not available for personal accounts" |

---

## Rollback Plan

1. Delete `tools/google_tools.py`
2. Revert changes to `google_auth.py` and `tool_registry.py`
3. Run `git checkout HEAD -- python/google_auth.py python/tools/tool_registry.py`
