from __future__ import annotations
import os
import json
from typing import Any, Dict, List
from .config import load_config, get_llm_config
from .llm import OpenAICompatibleLLM
from .tools import google_calendar as gcal
from .tools import notion as notion_tool
from .tools.smartlife import SmartLifeController
from .tools import web as web_tool
from .tools import browser as browser_tool
from .tools import calc as calc_tool
from .tools import wiki as wiki_tool
from .tools import news as news_tool
from .tools import fun as fun_tool
from .tools import weather as weather_tool
from .tools import time_tool
from .tools import macos as mac
from .tools import location as location_tool
from . import memory as memory_tool
from .tools import system as system_tool


class Agent:
    def __init__(self, cfg_path: str = "config.yaml"):
        self.cfg = load_config(cfg_path)
        self.llm = OpenAICompatibleLLM(get_llm_config(self.cfg))
        tools_cfg = self.cfg.get("tools", {})
        self.enable_gcal = tools_cfg.get("google_calendar", {}).get("enabled", False)
        self.enable_notion = tools_cfg.get("notion", {}).get("enabled", False)
        self.enable_smartlife = tools_cfg.get("smartlife", {}).get("enabled", False)
        self.smartlife = None
        if self.enable_smartlife:
            self.smartlife = SmartLifeController(tools_cfg.get("smartlife", {}).get("devices", {}))
        # Load personality (optional)
        self.persona = self._load_persona()

    def _load_persona(self) -> str:
        """Load a concise persona string from personality.yaml if present.
        Uses importlib to avoid hard dependency on PyYAML during static analysis.
        """
        try:
            import importlib as _importlib
            import json as _json
            path = os.getenv("PERSONALITY_FILE", "personality.yaml")
            if not os.path.exists(path):
                return ""
            data = {}
            if path.lower().endswith((".yaml", ".yml")):
                try:
                    _yaml = _importlib.import_module("yaml")
                except Exception:
                    return ""  # YAML file but no parser available; skip persona silently
                with open(path, "r", encoding="utf-8") as f:
                    data = _yaml.safe_load(f) or {}
            else:
                # Try JSON for non-YAML files
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = _json.loads(f.read())
                except Exception:
                    return ""
            tone = data.get("tone", {}) or {}
            style = tone.get("style", "friendly")
            humor = tone.get("humor", "light")
            formality = tone.get("formality", "medium")
            terseness = tone.get("terseness", "concise")
            guidelines = data.get("guidelines", []) or []
            gl = "; ".join(guidelines[:3]) if isinstance(guidelines, list) else str(guidelines)
            persona = (
                f"Persona: {style}, {humor} humor, {formality} tone, {terseness} replies. "
                + (f"Guidelines: {gl}" if gl else "")
            ).strip()
            return persona
        except Exception:
            return ""

    def _sanitize(self, text: str, user_text: str | None = None) -> str:
        # Remove obvious "thinking"/reasoning sections often wrapped in tags or brackets
        # Common patterns: <think>...</think>, ```thinking```, [thinking] ...
        import re
        patterns = [
            r"<think>[\s\S]*?</think>",            # remove closed think blocks
            r"```thinking[\s\S]*?```",             # fenced code block
            r"\[thinking\][\s\S]*?(?=\n|$)",    # bracketed tag
        ]
        cleaned = text
        for p in patterns:
            cleaned = re.sub(p, "", cleaned, flags=re.IGNORECASE)
        # If there is an unmatched <think>, drop everything from it to end
        if "<think>" in cleaned and "</think>" not in cleaned:
            cleaned = cleaned.split("<think>", 1)[0]
        # Remove lone <think> tokens that some models prepend
        cleaned = re.sub(r"\s*<think>\s*", "", cleaned, flags=re.IGNORECASE)
        # Trim leading labels like 'Assistant:' or 'Reply:' or 'Final answer:'
        cleaned = re.sub(r"^(assistant|reply|final\s*answer)\s*:\s*", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip()
        # Remove leading meta/header lines like '*Brainstorming*:' or 'Important:' etc.
        meta_line = re.compile(r"^\s*(?:\*+[^:*]+\*+|[A-Za-z\s-]+)\s*:\s*", re.IGNORECASE)
        lines = cleaned.splitlines()
        pruned: list[str] = []
        banned_prefixes = (
            "wait",
            "note",
            "let's",
            "i will",
            "i'll",
            "i should",
            "we should",
            "meta",
            "analysis",
            "reasoning",
            "brainstorming",
            "potential pitfall",
            "important",
            "system",
            "internal",
            "assistant should",
            "the user's message",
            "check for accuracy",
            "better keep",
        )
        for ln in lines:
            # Identify obvious meta markers at the start
            if re.match(r"^\s*(\*|_|-|\d+\.)?\s*(analysis|thoughts?|reasoning|brainstorming|plan|steps?|potential\s+pitfall|important|note|notes|critique|self-critique|internal|system|meta)\s*[:：]", ln, re.IGNORECASE):
                continue
            if meta_line.match(ln) and any(w in ln.lower() for w in ["brainstorm", "pitfall", "analysis", "reason", "meta", "internal", "outline", "plan", "notes", "important"]):
                continue
            # Drop bullets that label speakers
            if re.match(r"^\s*[-*]\s*(user|assistant|system)\s*[:：]", ln, re.IGNORECASE):
                continue
            # Drop lines that start with banned prefixes
            ln_trim = ln.strip().lower()
            if any(ln_trim.startswith(bp) for bp in banned_prefixes):
                continue
            pruned.append(ln)
        cleaned = "\n".join(pruned).strip()

        # If inner sentences still contain meta like "Wait, ...", remove those sentences
        def strip_meta_sentences(txt: str) -> str:
            # Simple sentence split by punctuation
            parts = re.split(r"(?<=[.!?])\s+", txt)
            keep: list[str] = []
            for s in parts:
                s_l = s.strip().lower()
                if not s_l:
                    continue
                if any(s_l.startswith(bp) for bp in banned_prefixes):
                    continue
                if any(k in s_l for k in ("the user's message", "assistant should", "i should", "let's")):
                    continue
                keep.append(s.strip())
            return " ".join(keep).strip()

        cleaned = strip_meta_sentences(cleaned)
        if cleaned and not cleaned.lower().startswith("<think"):
            # Avoid echoing the user's last utterance
            if user_text and cleaned.strip().lower() == user_text.strip().lower():
                return "Got it."
            return cleaned

        # Fallback: try to extract after markers like 'Final answer:'
        m = re.search(r"(final\s*answer|answer|assistant|reply)\s*:\s*([\s\S]+)$", text, flags=re.IGNORECASE)
        if m:
            ans = m.group(2).strip()
            if user_text and ans.strip().lower() == user_text.strip().lower():
                return "Understood."
            return ans

        # Next fallback: choose the last non-empty line without tags
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        for ln in reversed(lines):
            if not any(tag in ln.lower() for tag in ("<think>", "</think>", "```", "[thinking]")):
                if user_text and ln.strip().lower() == user_text.strip().lower():
                    return "Understood."
                return ln

        # Last resort: a friendly short reply
        return "All good here—how can I help?"

    def handle_text(self, text: str) -> str:
        # Simple router: call LLM to interpret intent and decide tool usage
        persona = (self.persona + " ") if getattr(self, "persona", "") else ""
        system = (
            persona +
            "You are a helpful desktop assistant with tools to manage Google Calendar, Notion, and SmartLife devices. "
            "You also have tools for web search, web fetch, current time, approximate location, macOS Music control, battery status, timers and stopwatches, opening common websites, YouTube search, and quick weather reports. "
            "Respond with the final answer only. Do not include your chain-of-thought, analysis, or thinking tags. "
            "When asked to perform an action requiring tools, output a JSON object on a single line with keys: tool, action, args. "
            "Tools: gcal(list_events|create_event), notion(create_page|search), smartlife(turn_on|turn_off|set_brightness), "
            "web(search|fetch), time(now), location(whereami), music(play|pause|toggle|next|previous), "
            "battery(status), timer(start|cancel|status), stopwatch(start|stop|reset|status), shortcuts(run), "
            "memory(add|search|clear), browser(open_youtube|open_github|open_instagram|yt_trending|search_youtube|open_website), "
            "weather(report), system(open_app|quit_app|close_window|fullscreen|volume_up|volume_down|mute|unmute), "
            "calc(calculate), wiki(summary|search), news(headlines), fun(joke|coin|dice)."
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": text},
            {"role": "system", "content": "If no tool is needed, answer naturally. If a tool is needed, ONLY output JSON."},
        ]
        try:
            result = self.llm.chat(messages, temperature=0.2, max_tokens=192)
            content = result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            msg = str(e)
            if "LM Studio server is offline." in msg:
                return "LM Studio server is offline."
            # Generic fallback
            return f"I couldn't reach the AI service: {e}"
        # Try to parse tool call JSON
        try:
            data = json.loads(content)
            if not isinstance(data, dict) or "tool" not in data:
                raise ValueError("not a tool call")
            try:
                return self._execute_tool(data)
            except Exception as e:
                return f"Tool error: {e}"
        except Exception:
            # fallback: just return the content
            return self._sanitize(content, user_text=text)

    def answer_with_web_grounding(self, question: str) -> str:
        """Search, fetch a few sources, and answer using only grounded snippets with brief citations."""
        try:
            try:
                k = int(os.getenv("WEB_SEARCH_K", "5"))
            except Exception:
                k = 5
            results = web_tool.search(question, k=k)
        except Exception:
            results = []
        if not results or not isinstance(results, list):
            # Fall back to normal handling
            return self.handle_text(question)

        def _extract_snippets(full_text: str, q: str, max_chars: int = 1600, max_sentences: int = 5) -> str:
            import re as _re
            text = (full_text or "").strip()
            if not text:
                return ""
            # Sentence split: keep it simple
            sentences = _re.split(r"(?<=[.!?])\s+", text)
            # Build keyword set from question (words >= 3 chars)
            kws = set(w.lower() for w in _re.findall(r"[A-Za-z0-9]+", q) if len(w) >= 3)
            def score(s: str) -> int:
                sl = s.lower()
                hits = sum(1 for k in kws if k in sl)
                nums = 1 if _re.search(r"\d", s) else 0
                return hits * 2 + nums
            # Rank sentences by relevance
            ranked = sorted(sentences, key=score, reverse=True)
            picked = []
            total = 0
            for s in ranked:
                st = s.strip()
                if not st:
                    continue
                picked.append(st)
                total += len(st) + 1
                if len(picked) >= max_sentences or total >= max_chars:
                    break
            if not picked:
                picked = sentences[:max_sentences]
            out = " ".join(picked)
            return out[:max_chars]

        # Fetch top N pages (default 1 for speed) and extract relevant snippets
        try:
            max_sources = int(os.getenv("WEB_SOURCES", "1"))
        except Exception:
            max_sources = 1
        corpus = []
        for r in results[:max_sources]:
            if not isinstance(r, dict):
                continue
            url = r.get("url", "")
            if not url:
                continue
            text = web_tool.fetch_text(url)
            if text and not text.lower().startswith("fetch error"):
                snippet = _extract_snippets(text, question, max_chars=1200, max_sentences=5)
                if snippet:
                    corpus.append({"url": url, "title": r.get("title", url), "text": snippet})
        if not corpus:
            return self.handle_text(question)

        # Build a grounded prompt with compact source list; avoid raw URLs in text body
        indexed = []
        for i, c in enumerate(corpus, start=1):
            domain = c.get('url', '')
            try:
                # Extract domain for readability
                import re as _re
                m = _re.search(r"https?://([^/]+)", domain)
                domain = m.group(1) if m else domain
            except Exception:
                pass
            title = c.get('title') or domain
            indexed.append((i, title, c.get('url', ''), c.get('text', '')))

        sources_blob = "\n\n".join(
            f"[{i}] {title} — {url}\n{text}" for (i, title, url, text) in indexed
        )
        messages = [
            {"role": "system", "content": (
                "You are a verifier-summarizer. Answer the user's question STRICTLY using the provided sources. "
                "Prefer a single best source when possible for speed and clarity. "
                "If the answer is not present, say 'I couldn't verify that.' Do not list search results. "
                "Give a direct, concise answer (1–2 sentences). Include a short bracket citation like [1]; avoid multiple citations unless essential. "
                "Do NOT paste raw URLs in the prose; use only bracket numbers. If the user asks for a quantity (e.g., 'highest score'), answer with the number and brief context."
            )},
            {"role": "system", "content": sources_blob},
            {"role": "user", "content": question},
        ]
        def _ask(msgs):
            # Keep token budget modest to improve latency on local servers
            return self.llm.chat(msgs, temperature=0.1, max_tokens=128)
        try:
            result = _ask(messages)
            reply = result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            # If context-related or 400 errors, retry with fewer/shorter sources
            emsg = str(e)
            if any(tok in emsg.lower() for tok in ("context", "tokens to keep", "too long", "400")):
                small_corpus = corpus[:1]
                sources_blob_small = "\n\n".join(
                    f"[{i+1}] {c['title']} — {c['url']}\n{c['text'][:800]}" for i, c in enumerate(small_corpus)
                )
                messages_small = [
                    messages[0],
                    {"role": "system", "content": sources_blob_small},
                    messages[-1],
                ]
                try:
                    result = _ask(messages_small)
                    reply = result["choices"][0]["message"]["content"].strip()
                except Exception as e2:
                    msg2 = str(e2)
                    if "LM Studio server is offline." in msg2:
                        return "LM Studio server is offline."
                    return f"I couldn't reach the AI service: {e2}"
            else:
                # As a last resort (e.g., timeouts), answer quickly without web grounding
                try:
                    quick = [
                        {"role": "system", "content": (
                            "Answer the user's question in one short sentence. "
                            "If you are unsure, say 'I couldn't verify that.' Do not include URLs or lists."
                        )},
                        {"role": "user", "content": question},
                    ]
                    result = self.llm.chat(quick, temperature=0.2, max_tokens=64)
                    reply = result["choices"][0]["message"]["content"].strip()
                except Exception as e3:
                    msg3 = str(e3)
                    if "LM Studio server is offline." in msg3:
                        return "LM Studio server is offline."
                    return f"I couldn't reach the AI service: {e}"
        # Sanitize and optionally append a non-spoken source list for console visibility
        ans = self._sanitize(reply, user_text=question)
        # If user wants visible sources in console, append on new lines; the TTS layer will strip URLs/citations as configured
        if os.getenv("PRINT_SOURCES", "1") == "1":
            lines = [ans, "", "Sources:"]
            for (i, title, url, _text) in indexed:
                lines.append(f"[{i}] {title} — {url}")
            ans = "\n".join(lines)
        return ans

    def _execute_tool(self, data: Dict[str, Any]) -> str:
        tool = data.get("tool")
        action = data.get("action")
        args = data.get("args", {})
        # Normalize args: allow string args and try to coerce to dict
        if not isinstance(args, dict):
            if isinstance(args, str):
                try:
                    parsed = json.loads(args)
                    if isinstance(parsed, dict):
                        args = parsed
                    else:
                        args = {"value": args}
                except Exception:
                    args = {"value": args}
            else:
                # Fallback to empty dict if unexpected type
                args = {}

        if tool == "gcal" and self.enable_gcal:
            if action == "list_events":
                max_results = int(args.get("max_results", 5))
                events = gcal.list_events(max_results=max_results)
                if not events:
                    return "No upcoming events found."
                return "\n".join(
                    f"- {e['summary']} at {e['start']}" for e in events
                )
            if action == "create_event":
                summary = args.get("summary")
                start = args.get("start")
                end = args.get("end")
                description = args.get("description")
                location = args.get("location")
                if not (summary and start and end):
                    return "Missing summary/start/end."
                created = gcal.create_event(summary, start, end, description, location)
                return f"Created event {summary}. Link: {created.get('htmlLink','')}"

        if tool == "notion" and self.enable_notion:
            if action == "create_page":
                db_id = self.cfg.get("tools", {}).get("notion", {}).get("default_database_id")
                title = args.get("title")
                properties = args.get("properties")
                if not db_id or not title:
                    return "Missing Notion database id or title."
                page = notion_tool.create_page_in_database(db_id, title, properties)
                return f"Created Notion page titled '{title}'."
            if action == "search":
                query = args.get("query", "")
                results = notion_tool.search(query)
                return f"Found {len(results)} results."

        if tool == "smartlife" and self.enable_smartlife and self.smartlife:
            name = args.get("name")
            if not name:
                return "Missing device name."
            if action == "turn_on":
                return self.smartlife.turn_on(name)
            if action == "turn_off":
                return self.smartlife.turn_off(name)
            if action == "set_brightness":
                percent = int(args.get("percent", 100))
                return self.smartlife.set_brightness(name, percent)

        # Web/time/location tools are always available by default
        if tool == "web":
            if action == "search":
                q = str(args.get("query") or args.get("q") or args.get("value") or "")
                k = int(args.get("k", 5))
                results = web_tool.search(q, k=k)
                if not results:
                    return "No results found."
                # Summarize top results concisely (title + domain only)
                def _domain(u: str) -> str:
                    try:
                        import re as _re
                        m = _re.search(r"https?://([^/]+)", u)
                        return m.group(1) if m else u
                    except Exception:
                        return u
                return "\n".join(f"- {r['title']} [{_domain(r['url'])}]" for r in results)
            if action == "fetch":
                url = str(args.get("url") or args.get("value") or "")
                if not url:
                    return "Missing url."
                text = web_tool.fetch_text(url)
                return text[:1000] + ("…" if len(text) > 1000 else "")

        if tool == "time" and action == "now":
            return time_tool.now()

        if tool == "location" and action == "whereami":
            city, region, country = location_tool.where_am_i()
            return ", ".join([p for p in [city, region, country] if p]) or "Location unavailable."

        # Browser helpers
        if tool == "browser":
            if action == "open_youtube":
                return browser_tool.open_youtube()
            if action == "open_github":
                return browser_tool.open_github()
            if action == "open_instagram":
                return browser_tool.open_instagram()
            if action == "yt_trending":
                return browser_tool.yt_trending()
            if action == "search_youtube":
                topic = str(args.get("topic") or args.get("query") or args.get("value") or "").strip()
                return browser_tool.search_youtube(topic)
            if action == "open_website":
                target = str(args.get("url") or args.get("site") or args.get("value") or "").strip()
                return browser_tool.open_website(target)

        # Weather quick report
        if tool == "weather" and action in ("report", "weather", "get"):
            city = str(args.get("city") or args.get("location") or args.get("q") or args.get("value") or "").strip()
            if not city:
                return "Missing city/location."
            rep = weather_tool.weather_report(city)
            if isinstance(rep, dict) and "error" in rep:
                return rep["error"]
            # Summarize into a short spoken-friendly line
            t = rep.get("temperature_c")
            w = rep.get("wind_kph")
            cond = rep.get("condition")
            hum = rep.get("humidity")
            bits = [f"Weather in {rep.get('city','')}"]
            if cond:
                bits.append(str(cond))
            if t is not None:
                bits.append(f"{t}°C")
            if hum is not None:
                bits.append(f"{hum}% humidity")
            if w is not None:
                bits.append(f"wind {w} kph")
            return ", ".join(bits)

        # Calculator
        if tool == "calc":
            if action in ("calculate", "calc", "eval"):
                expr = str(args.get("expr") or args.get("expression") or args.get("value") or "").strip()
                return calc_tool.calculate(expr)

        # Wikipedia
        if tool == "wiki":
            if action in ("summary", "lookup"):
                topic = str(args.get("topic") or args.get("query") or args.get("value") or "").strip()
                return wiki_tool.summary(topic)
            if action == "search":
                query = str(args.get("query") or args.get("value") or "").strip()
                hits = wiki_tool.search(query)
                if not hits:
                    return "No results found."
                return "\n".join(f"- {h['title']}" for h in hits)

        # News
        if tool == "news":
            if action in ("headlines", "news"):
                try:
                    limit = int(args.get("limit", 5))
                except Exception:
                    limit = 5
                heads = news_tool.headlines(limit=limit)
                return "\n".join(f"- {h}" for h in heads) if heads else "No headlines."

        # Fun
        if tool == "fun":
            if action == "joke":
                return fun_tool.joke()
            if action == "coin":
                return fun_tool.coin()
            if action in ("dice", "roll"):
                sides = int(args.get("sides", 6)) if isinstance(args, dict) else 6
                return fun_tool.dice(sides)

        # System control
        if tool == "system":
            if action == "open_app":
                name = str(args.get("app") or args.get("name") or args.get("value") or "").strip()
                return system_tool.open_app(name)
            if action == "quit_app":
                name = str(args.get("app") or args.get("name") or args.get("value") or "").strip()
                return system_tool.quit_app(name)
            if action == "close_window":
                return system_tool.close_window()
            if action == "fullscreen":
                return system_tool.fullscreen_toggle()
            if action == "volume_up":
                step = int(args.get("step", 10)) if isinstance(args, dict) else 10
                return system_tool.volume_up(step)
            if action == "volume_down":
                step = int(args.get("step", 10)) if isinstance(args, dict) else 10
                return system_tool.volume_down(step)
            if action == "mute":
                return system_tool.mute()
            if action == "unmute":
                return system_tool.unmute()

        # macOS tools
        if tool == "music":
            act = str(args.get("action") or action or "").lower()
            return mac.music(act)

        if tool == "battery":
            if action in ("status", None, ""):
                return mac.battery_status()
            return "Unsupported battery action. Use 'status'."

        if tool == "timer":
            if action == "start":
                try:
                    seconds = int(args.get("seconds", 0))
                except Exception:
                    seconds = 0
                return mac.start_timer(seconds)
            if action == "cancel":
                return mac.cancel_timers()
            if action == "status":
                return mac.timers_status()
            return "Unsupported timer action. Use start|cancel|status."

        if tool == "stopwatch":
            if action == "start":
                return mac.stopwatch_start()
            if action == "stop":
                return mac.stopwatch_stop()
            if action == "reset":
                return mac.stopwatch_reset()
            if action == "status":
                return mac.stopwatch_status()
            return "Unsupported stopwatch action. Use start|stop|reset|status."

        if tool == "shortcuts":
            if action == "run":
                name = args.get("name") or args.get("shortcut") or args.get("value")
                input_text = args.get("input")
                return mac.run_shortcut(str(name or ""), str(input_text) if input_text is not None else None)
            return "Unsupported shortcuts action. Use run."

        # Memory tools (always available)
        if tool == "memory":
            if action == "add":
                text = str(args.get("text") or args.get("value") or "").strip()
                return memory_tool.add_memory(text)
            if action == "search":
                query = str(args.get("query") or args.get("value") or "").strip()
                try:
                    limit = int(args.get("limit", 5))
                except Exception:
                    limit = 5
                hits = memory_tool.search_memories(query, limit=limit)
                return "\n".join(f"- {h}" for h in hits) if hits else "No memories found."
            if action == "clear":
                return memory_tool.clear_memories()
            return "Unsupported memory action. Use add|search|clear."

        return "Tool/action not available or not enabled."

    def _finalize(self, text: str) -> str:
        """Trim to a short, clean answer: remove lingering meta and limit to 1-2 sentences."""
        import re
        s = (text or "").strip()
        # Remove any trailing meta paragraphs that might remain after sanitize
        bad_tokens = (
            "wait,", "assistant should", "the user's", "i should", "let's", "meta", "analysis", "reasoning",
        )
        # Drop lines containing bad tokens
        lines = [ln for ln in s.splitlines() if ln.strip() and not any(bt in ln.lower() for bt in bad_tokens)]
        s = " ".join(lines).strip() or text.strip()
        # Keep only first 1-2 sentences
        parts = re.split(r"(?<=[.!?])\s+", s)
        clean_parts: list[str] = []
        for p in parts:
            pl = p.strip().lower()
            if not p.strip():
                continue
            if any(bt in pl for bt in bad_tokens):
                continue
            clean_parts.append(p.strip())
            if len(clean_parts) >= 2:
                break
        out = " ".join(clean_parts).strip()
        return out or (s.split("\n", 1)[0].strip() if s else "Okay.")


class ChatSession:
    """Lightweight conversational wrapper that keeps dialogue history."""

    def __init__(self, cfg_path: str = "config.yaml"):
        self.agent = Agent(cfg_path)
        persona = getattr(self.agent, "persona", "")
        persona_line = (persona + " ") if persona else ""
        self.history: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"{persona_line}You are a fast, conversational personal assistant. Keep replies short and friendly. "
                    "Reply with the final answer ONLY. Do not include analysis, steps, plans, brainstorming, or meta comments. "
                    "Avoid headings like 'Important:' or '*Brainstorming*:'. If a tool is required, the Agent will handle it."
                ),
            }
        ]
        # Load phrase->shortcut aliases from env
        self.shortcut_aliases: dict[str, str] = {}
        raw_aliases = os.getenv("SHORTCUTS_ALIASES", "").strip()
        if raw_aliases:
            # Support JSON mapping or simple "phrase1:Shortcut One; phrase2:Shortcut Two" syntax
            try:
                if raw_aliases.startswith("{"):
                    import json as _json
                    mapping = _json.loads(raw_aliases)
                    if isinstance(mapping, dict):
                        self.shortcut_aliases = {str(k).lower().strip(): str(v).strip() for k, v in mapping.items()}
                else:
                    pairs = [p for p in (seg.strip() for seg in raw_aliases.split(";")) if p]
                    for pair in pairs:
                        if ":" in pair:
                            k, v = pair.split(":", 1)
                        elif "=>" in pair:
                            k, v = pair.split("=>", 1)
                        else:
                            continue
                        k = k.strip().lower()
                        v = v.strip()
                        if k and v:
                            self.shortcut_aliases[k] = v
            except Exception:
                # ignore malformed aliases
                self.shortcut_aliases = {}

    def ask(self, text: str) -> str:
        # Route through Agent if tools required; else chat directly for low latency.
        # We first try a quick assistant reply without tools.
        # If always factchecking is enabled or text looks factual, use grounded path.
        smalltalk_triggers = (
            "hi", "hello", "hey", "how are you", "how you doing", "what's up", "whats up", "good morning", "good evening", "good night"
        )
        ql = text.lower().strip()
        is_smalltalk = any(t in ql for t in smalltalk_triggers)

        # Explicit routing for local time queries to avoid web grounding or LLM chatter
        time_patterns = (
            "what time is it",
            "what's the time",
            "whats the time",
            "current time",
            "time now",
        )
        if any(p in ql for p in time_patterns) or ql == "time":
            try:
                # Use the time tool directly
                return self.agent._execute_tool({"tool": "time", "action": "now", "args": {}})
            except Exception:
                # Fallback to quick LLM if tool fails for any reason
                pass

        # Direct music control phrases
        music_map = {
            "play music": "play",
            "pause music": "pause",
            "resume music": "play",
            "toggle music": "toggle",
            "next song": "next",
            "previous song": "previous",
            "skip song": "next",
        }
        for phrase, act in music_map.items():
            if phrase in ql:
                return self.agent._execute_tool({"tool": "music", "action": act, "args": {"action": act}})

        # Simple system control phrases
        if ql.startswith("open "):
            app = text.split("open ", 1)[1].strip()
            if app:
                return self.agent._execute_tool({"tool": "system", "action": "open_app", "args": {"app": app}})
        if ql.startswith("quit ") or ql.startswith("close "):
            # 'close window' handled separately; this is 'quit app'
            if ql.startswith("close window"):
                return self.agent._execute_tool({"tool": "system", "action": "close_window", "args": {}})
            app = text.split(" ", 1)[1].strip()
            if app:
                return self.agent._execute_tool({"tool": "system", "action": "quit_app", "args": {"app": app}})
        if ql in ("close window", "close this window"):
            return self.agent._execute_tool({"tool": "system", "action": "close_window", "args": {}})
        if ql in ("fullscreen", "toggle fullscreen"):
            return self.agent._execute_tool({"tool": "system", "action": "fullscreen", "args": {}})
        if ql in ("volume up", "increase volume"):
            return self.agent._execute_tool({"tool": "system", "action": "volume_up", "args": {}})
        if ql in ("volume down", "decrease volume"):
            return self.agent._execute_tool({"tool": "system", "action": "volume_down", "args": {}})
        if ql in ("mute", "mute volume"):
            return self.agent._execute_tool({"tool": "system", "action": "mute", "args": {}})
        if ql in ("unmute", "unmute volume"):
            return self.agent._execute_tool({"tool": "system", "action": "unmute", "args": {}})

        # Quick browser openers
        if ql in ("open youtube", "youtube"):
            return self.agent._execute_tool({"tool": "browser", "action": "open_youtube", "args": {}})
        if ql in ("open github", "github"):
            return self.agent._execute_tool({"tool": "browser", "action": "open_github", "args": {}})
        if ql in ("open instagram", "instagram"):
            return self.agent._execute_tool({"tool": "browser", "action": "open_instagram", "args": {}})
        if ql in ("youtube trending", "open youtube trending", "trending on youtube"):
            return self.agent._execute_tool({"tool": "browser", "action": "yt_trending", "args": {}})
        if ql.startswith("search youtube for "):
            topic = text.split("search youtube for ", 1)[1].strip()
            return self.agent._execute_tool({"tool": "browser", "action": "search_youtube", "args": {"topic": topic}})
        # Open arbitrary website
        if ql.startswith("open website "):
            site = text.split("open website ", 1)[1].strip()
            return self.agent._execute_tool({"tool": "browser", "action": "open_website", "args": {"value": site}})
        # Open domain shortcuts like 'open reddit.com'
        if ql.startswith("open ") and "." in ql and " " not in ql.split(" ", 1)[1]:
            site = text.split("open ", 1)[1].strip()
            return self.agent._execute_tool({"tool": "browser", "action": "open_website", "args": {"value": site}})

        # Weather
        import re as _re
        m = _re.match(r"(?:what's|whats|what is|tell me|give me)?\s*(?:the\s*)?weather(?:\s+in\s+|\s+at\s+|\s+for\s+)?(.+)$", ql)
        if m:
            city = m.group(1).strip()
            if city and len(city.split()) <= 5:  # keep it compact; avoids over-matching paragraphs
                return self.agent._execute_tool({"tool": "weather", "action": "report", "args": {"city": city}})

        # Calculator quick phrases
        if ql.startswith("calculate ") or ql.startswith("calc "):
            expr = text.split(" ", 1)[1]
            return self.agent._execute_tool({"tool": "calc", "action": "calculate", "args": {"expr": expr}})

        # Wikipedia quick lookup
        if ql.startswith("who is ") or ql.startswith("what is ") or ql.startswith("who was "):
            topic = text.split(" ", 2)[2] if len(text.split(" ")) >= 3 else text
            # prefer wiki summary which is concise; fall back to grounded web for complex questions
            if len(topic.split()) <= 8:
                return self.agent._execute_tool({"tool": "wiki", "action": "summary", "args": {"topic": topic}})

        # News
        if ql in ("news", "headlines", "what's the news", "latest news"):
            return self.agent._execute_tool({"tool": "news", "action": "headlines", "args": {"limit": 5}})

        # Fun utilities
        if ql in ("tell me a joke", "joke"):
            return self.agent._execute_tool({"tool": "fun", "action": "joke", "args": {}})
        if ql in ("flip a coin", "coin toss", "coin"):
            return self.agent._execute_tool({"tool": "fun", "action": "coin", "args": {}})
        if ql.startswith("roll a dice") or ql.startswith("roll a die") or ql.startswith("roll d"):
            # support 'roll d20' style
            import re as _re
            m = _re.search(r"roll\s+d?(\d+)", ql)
            sides = int(m.group(1)) if m else 6
            return self.agent._execute_tool({"tool": "fun", "action": "dice", "args": {"sides": sides}})

        # Direct stopwatch control
        if ql.startswith("start stopwatch") or ql == "start the stopwatch":
            return self.agent._execute_tool({"tool": "stopwatch", "action": "start", "args": {}})
        if ql.startswith("stop stopwatch") or ql == "stop the stopwatch":
            return self.agent._execute_tool({"tool": "stopwatch", "action": "stop", "args": {}})
        if ql.startswith("reset stopwatch") or ql == "reset the stopwatch":
            return self.agent._execute_tool({"tool": "stopwatch", "action": "reset", "args": {}})
        if ql.startswith("stopwatch status") or ql == "what's the stopwatch" or ql == "stopwatch":
            return self.agent._execute_tool({"tool": "stopwatch", "action": "status", "args": {}})

        # Direct timer phrases with simple natural parsing (minutes/seconds)
        # Examples: "set a timer for 5 minutes", "start a 30 second timer"
        import re as _re
        m = _re.search(r"(\d+)\s*(second|seconds|sec|s|minute|minutes|min|m)\b", ql)
        if ("timer" in ql or "set a timer" in ql or "start a timer" in ql) and m:
            num = int(m.group(1))
            unit = m.group(2)
            seconds = num * 60 if unit.startswith("m") else num
            return self.agent._execute_tool({"tool": "timer", "action": "start", "args": {"seconds": seconds}})
        if ql in ("cancel timer", "stop timer", "clear timer", "cancel the timer", "stop the timer"):
            return self.agent._execute_tool({"tool": "timer", "action": "cancel", "args": {}})
        if ql in ("timer status", "what's the timer", "timers", "timer"):
            return self.agent._execute_tool({"tool": "timer", "action": "status", "args": {}})

        # Direct memory phrases: remember/search/clear
        if ql.startswith("remember "):
            to_save = text[len(text.lower().split("remember ", 1)[0]) + len("remember "):].strip()
            if to_save:
                return self.agent._execute_tool({"tool": "memory", "action": "add", "args": {"text": to_save}})
        if ql.startswith("recall ") or ql.startswith("find in memory ") or ql.startswith("search memory "):
            query = text.split(" ", 1)[1] if " " in text else ""
            return self.agent._execute_tool({"tool": "memory", "action": "search", "args": {"query": query}})
        if ql in ("clear memories", "clear memory", "reset memories"):
            return self.agent._execute_tool({"tool": "memory", "action": "clear", "args": {}})

        # Lightweight shortcut runner: "run shortcut <name>"
        if ql.startswith("run shortcut"):
            # Extract quoted name if present, else take rest of the string
            import re as _re
            m = _re.search(r"run\s+shortcut\s+\"([^\"]+)\"|run\s+shortcut\s+'([^']+)'|run\s+shortcut\s+(.+)$", text, _re.IGNORECASE)
            name = None
            if m:
                name = m.group(1) or m.group(2) or m.group(3)
            if name:
                return self.agent._execute_tool({"tool": "shortcuts", "action": "run", "args": {"name": name.strip()}})

        # Aliases: direct phrase to specific shortcut
        if self.shortcut_aliases:
            alias_key = ql.strip('"\'')
            if alias_key in self.shortcut_aliases:
                return self.agent._execute_tool({"tool": "shortcuts", "action": "run", "args": {"name": self.shortcut_aliases[alias_key]}})
            # Also support "run <alias>" / "run the <alias>"
            for prefix in ("run ", "run the "):
                if alias_key.startswith(prefix):
                    key = alias_key[len(prefix):].strip()
                    if key in self.shortcut_aliases:
                        return self.agent._execute_tool({"tool": "shortcuts", "action": "run", "args": {"name": self.shortcut_aliases[key]}})

        if os.getenv("FACTCHECK_ALWAYS", "0") == "1" and not is_smalltalk:
            grounded = self.agent.answer_with_web_grounding(text)
            grounded = self.agent._finalize(grounded)
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": grounded})
            return grounded

        factual_triggers = (
            "who is", "who was", "what is", "what are", "when is", "when did", "where is", "how many", "how much",
            "current", "latest", "news", "population", "capital", "score", "rank", "list", "define", "definition"
        )
        if (any(ql.startswith(t) for t in factual_triggers) or "highest score" in ql) and not is_smalltalk:
            grounded = self.agent.answer_with_web_grounding(text)
            grounded = self.agent._finalize(grounded)
            self.history.append({"role": "user", "content": text})
            self.history.append({"role": "assistant", "content": grounded})
            return grounded
        quick_msgs = self.history + [{"role": "user", "content": text}]
        try:
            result = self.agent.llm.chat(quick_msgs, temperature=0.2, max_tokens=256)
            reply = result["choices"][0]["message"]["content"].strip()
            # Heuristic: if model returns a single-line JSON with tool call keywords, hand off to tool router
            if reply.startswith("{") and "\"tool\"" in reply:
                reply = self.agent.handle_text(text)
        except Exception:
            reply = self.agent.handle_text(text)
        # Sanitize and update history
        reply = self.agent._sanitize(reply, user_text=text)
        # If the sanitized reply is too generic/short, retry with the Agent's guided prompt
        generic_fallbacks = {
            "Got it.",
            "Understood.",
            "All good here—how can I help?",
        }
        if (reply in generic_fallbacks) or (len(reply.split()) < 4):
            try:
                guided = self.agent.handle_text(text)
                reply = self.agent._sanitize(guided, user_text=text)
            except Exception:
                pass
        # If meta patterns still slip through, try a direct one-shot answer instruction
        meta_tokens = (
            "assistant should", "the user's", "let's", "wait", "instructions say", "so the answer would be",
            "check for accuracy", "better keep",
        )
        if any(tok in reply.lower() for tok in meta_tokens):
            try:
                direct_msgs = [
                    {
                        "role": "system",
                        "content": (
                            "Answer the user's question directly in 1-2 sentences. "
                            "Do NOT include analysis, instructions, or meta commentary."
                        ),
                    },
                    {"role": "user", "content": text},
                ]
                direct = self.agent.llm.chat(direct_msgs, temperature=0.2, max_tokens=128)
                reply2 = direct["choices"][0]["message"]["content"].strip()
                reply = self.agent._sanitize(reply2, user_text=text)
            except Exception:
                pass
        # Final pass to keep the response concise and free of meta
        reply_final = self.agent._finalize(reply)
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply_final})
        return reply_final

    def ask_stream(self, text: str):
        """Yield partial text as it's generated. History is updated when completed."""
        # For simplicity, reuse the same routing as ask() but stream when going direct LLM.
        quick_msgs = self.history + [{"role": "user", "content": text}]
        accum = []
        try:
            for chunk in self.agent.llm.chat_stream(quick_msgs, temperature=0.2, max_tokens=256):
                accum.append(chunk)
                yield chunk
        except Exception:
            # If streaming fails, fall back to non-streaming
            final = self.ask(text)
            yield final
            return
        # Finalize once done
        reply = "".join(accum).strip()
        reply = self.agent._sanitize(reply, user_text=text)
        reply_final = self.agent._finalize(reply)
        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply_final})
