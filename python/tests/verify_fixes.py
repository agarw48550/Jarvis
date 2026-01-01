
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("🔍 Verifying Fixes...")

try:
    print("1. Testing Config Load...")
    from core.config import MODELS, API_KEYS
    print(f"   ✅ Config Loaded. Model: {MODELS.gemini_live_model}")
    
    print("2. Testing LLM Router Imports...")
    from core.llm_router import classify_task
    print(f"   ✅ Router Import OK. Classification Test ('write code'): {classify_task('write code')}")

    print("3. Testing Self-Evolution Imports...")
    from core.self_evolution import CodeAnalyzer
    print("   ✅ Self-Evolution Import OK.")

    print("4. Testing Jarvis CLI Imports...")
    import jarvis_live_cli
    print("   ✅ Jarvis CLI Import OK.")

    print("\n🎉 ALL CHECKS PASSED!")

except ImportError as e:
    print(f"\n❌ IMPORT ERROR: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ RUNTIME ERROR: {e}")
    sys.exit(1)
