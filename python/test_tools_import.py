import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent)) # jarvis/python

def test_imports():
    try:
        from tools.tool_registry import TOOLS
        print("✅ Tool Registry Imported")
        
        failed = False
        
        if "recall_conversation" in TOOLS:
            print("✅ recall_conversation registered")
        else:
            print("❌ recall_conversation MISSING")
            failed = True
            
        if "list_processes" in TOOLS:
            print("✅ list_processes registered")
        else:
            print("❌ list_processes MISSING")
            failed = True

        if "get_weather_legacy" in TOOLS:
            print("✅ get_weather_legacy registered")
        else:
            print("❌ get_weather_legacy MISSING")
            failed = True
            
        if not failed:
            print("🎉 All new tools verified in registry.")
            
    except Exception as e:
        print(f"❌ Import failed: {e}")

if __name__ == "__main__":
    test_imports()
