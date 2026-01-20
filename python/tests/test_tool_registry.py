
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.tool_registry import TOOLS
import json

print(f"Loaded {len(TOOLS)} tools.")

for name, info in TOOLS.items():
    print(f"- {name}: {info['description']}")
    # Test if function is callable
    fn = info['function']
    print(f"  Callable: {callable(fn)}")

# Test one simple tool
from tools.productivity_tools import get_time
print(f"Testing get_time: {get_time()}")
