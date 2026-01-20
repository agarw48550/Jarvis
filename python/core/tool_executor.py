import json
import re
from typing import List, Tuple, Any
from tools.tool_registry import TOOLS

def extract_and_execute_tools(response: str) -> Tuple[List[Tuple[str, Any]], str]:
    """Extract and execute tool calls from LLM response strings"""
    results = []
    
    # 1. Match code blocks: ```tool { ... } ```
    pattern_code_blocks = r'```tool\s*\n?(.*?)\n?```'
    matches_code = re.findall(pattern_code_blocks, response, re.DOTALL)
    
    # 2. Extract standalone JSON objects (brace counting)
    json_strs = []
    json_objects_found = []
    
    # Safe Initialization
    brace_count = 0  
    start_idx = -1   
    in_string = False
    escape = False
    
    for i, char in enumerate(response):
        if char == '"' and not escape:
            in_string = not in_string
        
        if char == '\\' and not escape:
            escape = True
        else:
            escape = False
            
        if not in_string:
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx >= 0:
                    json_str = response[start_idx:i+1]
                    try:
                        obj = json.loads(json_str)
                        if isinstance(obj, dict) and "tool" in obj and "params" in obj:
                            json_strs.append(json_str)
                            json_objects_found.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start_idx = -1

    # Combined results
    all_calls = []
    for match in matches_code:
        try:
            all_calls.append(json.loads(match.strip()))
        except json.JSONDecodeError: pass
    all_calls.extend(json_objects_found)

    # Process executions
    for tool_call in all_calls:
        try:
            tool_name = tool_call.get("tool")
            params = tool_call.get("params", {})
            
            if tool_name and tool_name in TOOLS:
                print(f"   🔧 Executing {tool_name}...")
                func = TOOLS[tool_name]["function"]
                # Clean params (remove None)
                params = {k: v for k, v in params.items() if v is not None}
                
                try:
                    result = func(**params) if params else func()
                except Exception as e:
                    result = f"Tool execution failed: {str(e)}"

                # Sanitize Result
                result_str = str(result)
                if len(result_str) > 10000:
                   result_str = result_str[:10000] + "... (truncated)"
                
                # Verify JSON serializability logic if needed, but for now just returning the string/obj
                # The caller (orchestrator/main) should handle JSON serialization
                results.append((tool_name, result_str))
        except Exception as e:
            results.append((tool_call.get("tool", "unknown"), f"Error: {e}"))

    # Clean the response text from tool markers
    clean = re.sub(pattern_code_blocks, '', response, flags=re.DOTALL)
    for json_str in json_strs:
        clean = clean.replace(json_str, '')
    
    # Fallback regex for remaining fragments
    clean = re.sub(r'\{\s*"tool"\s*:\s*"[^"]+"\s*,\s*"params"\s*:\s*\{[^}]*\}\s*\}', '', clean)
    
    return results, clean.strip()
