# Execution Notes

## Step 1: Update OAuth scopes in google_auth.py
- **Files changed:** `python/google_auth.py`
- **Changes:**
  - Added 4 new OAuth scopes: Drive readonly, Classroom courses/rosters readonly, Contacts readonly
  - Organized scopes with comments for clarity
- **Verify:** `python3 -m py_compile google_auth.py`
- **Result:** ✅ PASS

---

## Step 2: Create tools/google_tools.py
- **Files changed:** `python/tools/google_tools.py` (NEW)
- **Changes:**
  - Created new module with 8 functions: `list_drive_files`, `search_drive`, `list_classroom_courses`, `get_classroom_assignments`, `get_contacts`, `get_directions`, `get_places_nearby`, `get_timezone`
  - Follows existing pattern using `get_credentials()` and `googleapiclient.discovery.build`
  - Maps API tools use `GOOGLE_MAPS_API_KEY` from environment
- **Verify:** `python3 -m py_compile tools/google_tools.py`
- **Result:** ✅ PASS

---

## Step 3: Register tools in tool_registry.py
- **Files changed:** `python/tools/tool_registry.py`
- **Changes:**
  - Added import for all 8 functions from `tools.google_tools`
  - Added 8 new entries to `TOOLS` dictionary with descriptions and parameters
- **Verify:** `python3 -m py_compile tools/tool_registry.py`
- **Result:** ✅ PASS

---

## Step 4: Tool Registry Load Test
- **Command:** `python3 tests/test_tool_registry.py`
- **Result:** ✅ PASS
  - Loaded 46 tools (8 new Google tools)
  - All tools callable: True
