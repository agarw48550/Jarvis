"""
Jarvis Skills System
Loads and manages skill plugins from the skills directory and user's ~/.jarvis/skills/.
"""

import os
import importlib.util
import yaml
from pathlib import Path
from typing import Dict, Any


BUILTIN_SKILLS_DIR = Path(__file__).parent
USER_SKILLS_DIR = Path.home() / ".jarvis" / "skills"


class SkillLoader:
    """Discovers and loads Jarvis skills (plugins)."""
    
    def __init__(self):
        self.skills: Dict[str, dict] = {}
        self.skill_tools: Dict[str, dict] = {}  # tool_name -> tool_info
        self._scan_skills()
    
    def _scan_skills(self):
        """Scan both built-in and user skill directories."""
        for skills_dir in [BUILTIN_SKILLS_DIR, USER_SKILLS_DIR]:
            if not skills_dir.exists():
                continue
            
            for entry in skills_dir.iterdir():
                if entry.is_dir() and (entry / "SKILL.md").exists():
                    self._load_skill(entry)
    
    def _load_skill(self, skill_dir: Path):
        """Load a single skill from its directory."""
        skill_md = skill_dir / "SKILL.md"
        skill_name = skill_dir.name
        
        try:
            content = skill_md.read_text()
            metadata = self._parse_frontmatter(content)
            
            skill_info = {
                "name": metadata.get("name", skill_name),
                "description": metadata.get("description", "No description"),
                "version": metadata.get("version", "1.0"),
                "author": metadata.get("author", "unknown"),
                "path": str(skill_dir),
                "enabled": True,
                "tools": {}
            }
            
            # Load functions.py if it exists
            functions_file = skill_dir / "functions.py"
            if functions_file.exists():
                skill_tools = self._load_functions(functions_file, skill_name)
                skill_info["tools"] = skill_tools
                self.skill_tools.update(skill_tools)
            
            self.skills[skill_name] = skill_info
            tool_count = len(skill_info["tools"])
            print(f"🧩 [SKILLS] Loaded: {skill_info['name']} v{skill_info['version']} ({tool_count} tools)")
            
        except Exception as e:
            print(f"⚠️ [SKILLS] Failed to load skill '{skill_name}': {e}")
    
    def _parse_frontmatter(self, content: str) -> dict:
        """Parse YAML frontmatter from a SKILL.md file."""
        if not content.startswith("---"):
            return {}
        
        try:
            end = content.index("---", 3)
            frontmatter = content[3:end].strip()
            return yaml.safe_load(frontmatter) or {}
        except (ValueError, yaml.YAMLError):
            return {}
    
    def _load_functions(self, functions_file: Path, skill_name: str) -> Dict[str, dict]:
        """Load tool functions from a skill's functions.py file."""
        tools = {}
        
        try:
            spec = importlib.util.spec_from_file_location(
                f"skill_{skill_name}", str(functions_file)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for TOOLS dict or functions with @tool decorator
            if hasattr(module, 'TOOLS'):
                # Module exports a TOOLS dict directly
                tools = module.TOOLS
            else:
                # Auto-discover public functions with docstrings
                for attr_name in dir(module):
                    if attr_name.startswith('_'):
                        continue
                    func = getattr(module, attr_name)
                    if callable(func) and func.__doc__:
                        tool_name = f"{skill_name}_{attr_name}"
                        # Parse parameters from function signature
                        import inspect
                        sig = inspect.signature(func)
                        params = {}
                        for p_name, p in sig.parameters.items():
                            params[p_name] = p.annotation.__name__ if p.annotation != inspect.Parameter.empty else "string"
                        
                        tools[tool_name] = {
                            "function": func,
                            "description": func.__doc__.strip().split("\n")[0],
                            "parameters": {k: v for k, v in params.items()}
                        }
                        
        except Exception as e:
            print(f"⚠️ [SKILLS] Error loading functions from {functions_file}: {e}")
        
        return tools
    
    def list_skills(self) -> list:
        """Get list of all loaded skills."""
        return [
            {
                "name": s["name"],
                "description": s["description"],
                "version": s["version"],
                "enabled": s["enabled"],
                "tools": list(s["tools"].keys())
            }
            for s in self.skills.values()
        ]
    
    def enable_skill(self, name: str) -> bool:
        """Enable a skill by name."""
        if name in self.skills:
            self.skills[name]["enabled"] = True
            return True
        return False
    
    def disable_skill(self, name: str) -> bool:
        """Disable a skill by name."""
        if name in self.skills:
            self.skills[name]["enabled"] = False
            return True
        return False
    
    def get_enabled_tools(self) -> Dict[str, dict]:
        """Get all tools from enabled skills."""
        tools = {}
        for skill_name, skill_info in self.skills.items():
            if skill_info["enabled"]:
                tools.update(skill_info["tools"])
        return tools


# Singleton
_loader = None

def get_skill_loader() -> SkillLoader:
    """Get or create the global skill loader."""
    global _loader
    if _loader is None:
        _loader = SkillLoader()
    return _loader


# Tool functions for Jarvis to use
def list_skills() -> str:
    """List all installed Jarvis skills/plugins.
    
    Returns:
        Formatted list of skills with their status
    """
    loader = get_skill_loader()
    skills = loader.list_skills()
    
    if not skills:
        return "🧩 No skills installed. Add skills to ~/.jarvis/skills/ or the built-in skills directory."
    
    lines = ["🧩 Installed Skills:"]
    for s in skills:
        status = "✅" if s["enabled"] else "❌"
        tools_str = f" ({len(s['tools'])} tools)" if s['tools'] else ""
        lines.append(f"  {status} {s['name']} v{s['version']} — {s['description']}{tools_str}")
    
    return "\n".join(lines)


def enable_skill(skill_name: str) -> str:
    """Enable a Jarvis skill by name.
    
    Args:
        skill_name: Name of the skill to enable
    
    Returns:
        Confirmation message
    """
    loader = get_skill_loader()
    if loader.enable_skill(skill_name):
        return f"✅ Skill '{skill_name}' enabled."
    return f"⚠️ Skill '{skill_name}' not found."


def disable_skill(skill_name: str) -> str:
    """Disable a Jarvis skill by name.
    
    Args:
        skill_name: Name of the skill to disable
    
    Returns:
        Confirmation message
    """
    loader = get_skill_loader()
    if loader.disable_skill(skill_name):
        return f"✅ Skill '{skill_name}' disabled."
    return f"⚠️ Skill '{skill_name}' not found."
