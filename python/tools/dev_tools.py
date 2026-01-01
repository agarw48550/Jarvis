#!/usr/bin/env python3
"""
Development Tools for Self-Evolution (The "Terminal")
Allows Jarvis to write and execute code to extend its own capabilities.
"""

import os
import sys
import subprocess
import tempfile
import ast
from pathlib import Path
from typing import Optional

TOOLS_DIR = Path(__file__).parent
EXTENSIONS_DIR = TOOLS_DIR / "extensions"
EXTENSIONS_DIR.mkdir(exist_ok=True)

# Ensure extensions directory is in path
if str(EXTENSIONS_DIR) not in sys.path:
    sys.path.append(str(EXTENSIONS_DIR))

def validate_python_code(code: str) -> Optional[str]:
    """Syntax check Python code"""
    try:
        ast.parse(code)
        return None
    except SyntaxError as e:
        return f"Syntax Error on line {e.lineno}: {e.msg}"
    except Exception as e:
        return f"Error: {e}"

def write_extension(filename: str, code: str, overwrite: bool = False) -> str:
    """
    Write a new Python extension to tools/extensions/
    
    Args:
        filename: e.g., "stock_checker.py"
        code: The python source code
    """
    if not filename.endswith(".py"):
        filename += ".py"
        
    # Security: Prevent writing outside extensions dir
    try:
        file_path = (EXTENSIONS_DIR / filename).resolve()
        if not str(file_path).startswith(str(EXTENSIONS_DIR.resolve())):
            return "Error: Invalid filename. Path traversal detected."
    except Exception as e:
        return f"Error: Path validation failed: {e}"

    if file_path.exists() and not overwrite:
        return f"Error: Extension '{filename}' already exists. Use overwrite=True if you intend to replace it."
        
    # Syntax check
    error = validate_python_code(code)
    if error:
        return f"Cannot save: {error}"
        
    try:
        with open(file_path, "w") as f:
            f.write(code)
        return f"Successfully saved extension to {filename}. You can now load it."
    except Exception as e:
        return f"Failed to write file: {e}"

def run_python_script(code: str, timeout: int = 10) -> str:
    """
    Execute a Python script in a separate subprocess and return output.
    WARNING: This execution is NOT sandboxed and has the same permissions as the main process.
    Use this to test code before saving it as an extension.
    """
    # Syntax check
    error = validate_python_code(code)
    if error:
        return f"Syntax Error: {error}"
        
    # Create temp file
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code)
        temp_path = f.name
        
    try:
        # Run in subprocess with timeout
        result = subprocess.run(
            [sys.executable, temp_path],
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"
            
        return output.strip() or "(No output)"
        
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out."
    except Exception as e:
        return f"Execution failed: {e}"
    finally:
        # Cleanup
        try:
            os.unlink(temp_path)
        except OSError:
            pass

def list_extensions() -> str:
    """List all available extensions"""
    files = list(EXTENSIONS_DIR.glob("*.py"))
    if not files:
        return "No extensions found."
    return ", ".join([f.name for f in files])
