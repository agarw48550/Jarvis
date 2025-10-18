import os
import yaml
from dataclasses import dataclass
from typing import Any, Dict


def _env_expand(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
        key = value[2:-1]
        return os.getenv(key, "")
    if isinstance(value, dict):
        return {k: _env_expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_env_expand(v) for v in value]
    return value


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    with open(path, "r") as f:
        raw = yaml.safe_load(f) or {}
    expanded = _env_expand(raw)
    return expanded


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str


def get_llm_config(cfg: Dict[str, Any]) -> LLMConfig:
    llm = cfg.get("llm", {})
    base_url = llm.get("base_url") or "http://127.0.0.1:1234/v1"
    api_key = llm.get("api_key") or ""
    model = llm.get("model") or "qwen/qwen3-4b-2507"
    return LLMConfig(
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
