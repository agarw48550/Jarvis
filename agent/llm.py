import os
import requests
from typing import List, Dict, Any
from .config import LLMConfig
from typing import Iterator
import json as _json


class OpenAICompatibleLLM:
    def __init__(self, config: LLMConfig):
        base = config.base_url.strip()
        if base.endswith("/"):
            base = base[:-1]
        # If the base doesn't include "/v1" anywhere, append it for OpenAI-compatible paths
        if "/v1" not in base:
            base = base + "/v1"
        self.base_url = base
        self.api_key = config.api_key
        self.model = config.model
        host = self.base_url.lower()
        self._is_local = ("127.0.0.1" in host) or ("localhost" in host)
        self._is_thinking_model = "thinking" in (self.model or "").lower()
        self._validated_model = False
        self._debug = os.getenv("LLM_DEBUG", "0") == "1"

    def _log(self, msg: str):
        if self._debug:
            print(f"[LLM] {msg}")

    def _list_models(self):
        try:
            url = f"{self.base_url}/models"
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and isinstance(data.get("data"), list):
                return [m.get("id") for m in data["data"] if isinstance(m, dict)]
        except Exception as e:
            self._log(f"Failed to list models: {e}")
        return []

    def _ensure_model(self):
        if not self._is_local or self._validated_model:
            return
        available = self._list_models()
        if not available:
            self._log("No models listed by server; proceeding with configured model.")
            self._validated_model = True
            return
        if self.model in available:
            self._validated_model = True
            return
        # Try to find a reasonable fallback
        def pick(candidates):
            return candidates[0] if candidates else None
        prefer = [m for m in available if "instruct" in m.lower() and "reason" not in m.lower()]
        prefer_qwen = [m for m in prefer if "qwen" in m.lower()]
        chosen = pick(prefer_qwen) or pick(prefer) or pick(available)
        if chosen:
            self._log(f"Configured model '{self.model}' not found. Using '{chosen}'.")
            self.model = chosen
        self._validated_model = True

    def chat(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] | None = None,
             temperature: float = 0.3, max_tokens: int | None = None,
             stop: List[str] | None = None) -> Dict[str, Any]:
        # One-time model validation for local servers
        self._ensure_model()
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if self._debug:
            self._log(f"POST {url} model={self.model} temp={temperature} max_tokens={max_tokens}")
        # For local reasoning models, let them produce the final answer by not capping tokens
        if max_tokens is None:
            if self._is_local and self._is_thinking_model:
                payload["max_tokens"] = -1  # LM Studio supports -1 for unlimited
        else:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = stop
        if tools:
            payload["tools"] = tools
        # Give local servers (LM Studio) more time to respond even for non-reasoning models
        if self._is_local:
            # Allow override via env
            try:
                override = int(os.getenv("LLM_TIMEOUT", "0") or "0")
            except Exception:
                override = 0
            timeout = override or (30 if not self._is_thinking_model else 60)
        else:
            timeout = 15
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        except requests.exceptions.ConnectionError as ce:
            # Map connection refused / offline server to a concise message
            raise RuntimeError("LM Studio server is offline.") from ce
        except requests.exceptions.Timeout as te:
            raise RuntimeError("LM Studio server is offline.") from te
        if resp.status_code >= 400:
            # Surface server error details to aid debugging
            detail = None
            try:
                data = resp.json()
                # OpenAI-compatible error shape
                if isinstance(data, dict) and "error" in data:
                    err = data.get("error")
                    if isinstance(err, dict):
                        detail = err.get("message") or err.get("code")
                    else:
                        detail = str(err)
                else:
                    # Some servers return plain string messages
                    detail = str(data)
            except Exception:
                # Fallback to raw text
                detail = resp.text[:500]
            # If local server returns 400 (often invalid model), try auto-pick once
            if self._is_local and resp.status_code == 400 and not self._validated_model:
                self._validated_model = False  # force revalidation
                self._ensure_model()
                # Retry once with new model if changed
                if self._debug:
                    self._log(f"Retrying with model '{self.model}' after 400 error.")
                resp2 = requests.post(url, headers=headers, json={**payload, "model": self.model}, timeout=timeout)
                if resp2.status_code < 400:
                    return resp2.json()
                # Fall through with improved detail
                try:
                    data2 = resp2.json()
                    detail2 = data2.get("error", data2)
                except Exception:
                    detail2 = resp2.text[:500]
                raise requests.HTTPError(f"{resp2.status_code} {resp2.reason}: {detail2}")
            # If local server reports 4xx/5xx and looks like connection/availability issue
            if self._is_local and any(tok in str(detail).lower() for tok in ("connection refused", "unavailable", "failed to connect", "service unavailable")):
                raise RuntimeError("LM Studio server is offline.")
            raise requests.HTTPError(f"{resp.status_code} {resp.reason}: {detail}")
        return resp.json()

    def chat_stream(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]] | None = None,
                    temperature: float = 0.3, max_tokens: int | None = None,
                    stop: List[str] | None = None) -> Iterator[str]:
        """Stream text deltas from an OpenAI-compatible server (SSE /chat/completions)."""
        self._ensure_model()
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is None:
            if self._is_local and self._is_thinking_model:
                payload["max_tokens"] = -1
        else:
            payload["max_tokens"] = max_tokens
        if stop:
            payload["stop"] = stop
        if tools:
            payload["tools"] = tools
        timeout = 60 if self._is_local else 30
        with requests.post(url, headers=headers, json=payload, timeout=timeout, stream=True) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith(":"):
                    continue  # comment/keepalive
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = _json.loads(data)
                    delta = obj.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content")
                    if content:
                        yield content
                except Exception:
                    continue
