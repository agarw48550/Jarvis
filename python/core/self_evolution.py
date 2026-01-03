"""
Self-Evolution System for JARVIS
Allows the AI to analyze, improve, and safely modify its own codebase.
"""

import os
import re
import ast
import shutil
import logging
from typing import List, Dict, Tuple, Optional
from pathlib import Path
from datetime import datetime
from difflib import unified_diff
from core.llm_router import call_cerebras, call_groq, call_gemini

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SelfEvolution")

class SafetyGuard:
    """Prevents dangerous self-modifications"""
    
    PROTECTED_FILES = [
        "self_evolution.py",  # Can't modify itself
        ".env",
        "*.db",
        "gemini_quota.json"
    ]
    
    DANGEROUS_PATTERNS = [
        r"os\.system\(",
        r"subprocess\.run\([^)]*shell=True",
        r"eval\(",
        r"exec\(",
        r"__import__\(",
        r"shutil\.rmtree",
    ]
    
    def is_safe_modification(self, file_path: str, new_code: str) -> Tuple[bool, str]:
        """Check if proposed modification is safe"""
        path = Path(file_path)
        
        # 1. Check Protected Files
        if path.name in self.PROTECTED_FILES:
            return False, f"File {path.name} is protected from modification."
            
        # 2. Syntax Check
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            return False, f"Syntax Error: {e}"
            
        # 3. Dangerous Pattern Scan
        issues = self.scan_for_dangerous_code(new_code)
        if issues:
            return False, f"Dangerous patterns detected: {issues}"
            
        return True, "Safe"
    
    def scan_for_dangerous_code(self, code: str) -> List[str]:
        """Find potentially dangerous patterns in proposed code"""
        issues = []
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                issues.append(pattern)
        return issues


class CodeAnalyzer: 
    """Analyzes JARVIS source code for potential improvements"""
    
    def __init__(self):
        self.code_base_path = Path(__file__).parent.parent
    
    def get_all_source_files(self) -> List[Path]:
        """Get all Python files in the project"""
        return list(self.code_base_path.rglob("*.py"))
    
    def analyze_for_bugs(self, file_path: str) -> dict:
        """Use Cerebras (Logic) to find bugs"""
        code = Path(file_path).read_text(encoding='utf-8')
        prompt = f"""You are a senior Python developer reviewing code.
Analyze this code and identify bugs, performance issues, and security concerns.

Code to analyze:
```python
{code}
```

Respond in valid JSON format: {{ "bugs": [], "performance": [], "security": [] }}
"""
        response = call_cerebras([{"role": "user", "content": prompt}], "You are a code analyzer.")
        return response # Assuming response parses to dict or needs parsing

    def suggest_optimizations(self, file_path: str) -> dict:
        """Suggest performance improvements"""
        # Implementation via LLM
        pass


class CodeModifier:
    """Safely modifies JARVIS source code with user approval"""
    
    def __init__(self, analyzer: CodeAnalyzer):
        self.analyzer = analyzer
        self.backup_dir = Path(os.path.expanduser("~/.jarvis/backups"))
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.safety = SafetyGuard()
    
    def propose_change(self, file_path: str, request: str) -> dict:
        """Generate a proposed code change"""
        current_code = Path(file_path).read_text(encoding='utf-8')
        
        prompt = f"""You are modifying code for the JARVIS AI assistant.
Current code:
```python
{current_code}
```
User's request: {request}

Generate the improved code. Output ONLY the new code, no markdown fencing, no intro.
"""
        # Use Cerebras for coding capability
        new_code = call_cerebras([{"role": "user", "content": prompt}], "You are a Python expert.")
        
        # Clean up markdown if present
        if new_code.startswith("```python"):
            new_code = new_code.split("\n", 1)[1]
        if new_code.endswith("```"):
            new_code = new_code.rsplit("\n", 1)[0]
            
        return {
            "file_path": file_path,
            "old_code": current_code,
            "new_code": new_code,
            "diff": self._generate_diff(current_code, new_code)
        }
    
    def _generate_diff(self, old: str, new: str) -> str:
        old_lines = old.splitlines(keepends=True)
        new_lines = new.splitlines(keepends=True)
        return "".join(unified_diff(old_lines, new_lines, fromfile="Current", tofile="Proposed"))
    
    def apply_change(self, proposal: dict) -> bool:
        """Apply the change safely"""
        file_path = proposal["file_path"]
        new_code = proposal["new_code"]
        
        # Safety Check
        is_safe, reason = self.safety.is_safe_modification(file_path, new_code)
        if not is_safe:
            logger.error(f"Safety Check Failed: {reason}")
            return False
            
        # Backup
        self.backup_file(file_path)
        
        # Write
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            logger.info(f"Updated {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to write file: {e}")
            return False
    
    def backup_file(self, file_path: str) -> Path:
        """Create timestamped backup"""
        src = Path(file_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = self.backup_dir / f"{src.stem}_{timestamp}{src.suffix}"
        shutil.copy2(src, dst)
        return dst
    
    def rollback(self, file_path: str) -> bool:
        """Restore from most recent backup"""
        # Logic to find latest backup matching pattern and restore
        src_name = Path(file_path).stem
        backups = sorted(self.backup_dir.glob(f"{src_name}_*"))
        if not backups:
            return False
        latest = backups[-1]
        shutil.copy2(latest, file_path)
        return True


class AdaptiveLearner: 
    """Learns from user interactions to improve over time"""
    
    def __init__(self):
        self.preferences_file = Path(os.path.expanduser("~/.jarvis/preferences.json"))
    
    def record_feedback(self, query: str, response: str, rating: int):
        """Record user satisfaction"""
        # Logic to append to a JSON log
        pass
