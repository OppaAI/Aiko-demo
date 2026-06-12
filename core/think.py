"""
core/think.py

Aiko's cognitive loop.
  - Retrieves relevant memories before each turn
  - Tool routing: LLM-driven tool calling (preferred), with regex-based
    intent detection as fallback for weather, timezone, currency, joke,
    anime, and web search
  - Streams LLM response via token_callback
  - Stores the turn into long-term memory after each response (background thread)
  - Supports single-shot reasoning mode via set_reasoning(True) / /think command
"""

import os
import json
from datetime import datetime
import httpx
from pathlib import Path
import queue
import re
import threading

from core.memorize import AikoMemorize
from core.log      import get_logger

log = get_logger(__name__)

# ── boot labels ───────────────────────────────────────────────────────────────

BOOT_LABELS = {
    'think_start':  'Loading LLM client + persona...',
    'think_warmup': 'Warming up language model...',
}

# ── config ────────────────────────────────────────────────────────────────────

LLAMA_BASE_URL       = os.getenv("LLAMA_BASE_URL",  "https://your-modal-endpoint.modal.run")
LLAMA_MODEL          = os.getenv("LLAMA_MODEL",      "meta-llama/Llama-3.1-8B-Instruct")
LLAMA_API_KEY        = os.getenv("LLAMA_API_KEY",    "")
CONTEXT_WINDOW_TURNS = int(os.getenv("CONTEXT_WINDOW_TURNS", 20))

_BASE_PREDICT    = 400
_REASONING_SCALE = 3

_PERSONA_PATH = Path(__file__).resolve().parent.parent / "persona" / "soul.md"

_DEFAULT_USER_ID = os.getenv("USER_ID", "OppaAI")


def _render_persona(template: str, user_id: str) -> str:
    today = datetime.now().strftime("%B %d, %Y")
    return template.replace("USER_ID_HERE", user_id).replace("TODAY_HERE", today)


# ── think ─────────────────────────────────────────────────────────────────────

class AikoThink:
    """
    Aiko's conversational core.
    LLM warmup starts immediately on init in a background thread.
    wakeup.py calls join_warmup() to block until the model is hot.
    speak is accepted but ignored (kept for BootResult API compatibility).
    """

    def __init__(self, memorize: AikoMemorize, speak=None) -> None:
        headers = {"Content-Type": "application/json"}
        if LLAMA_API_KEY:
            headers["Authorization"] = f"Bearer {LLAMA_API_KEY}"

        self._client = httpx.Client(
            base_url=LLAMA_BASE_URL,
            headers=headers,
            timeout=120.0,
        )
        self._memorize  = memorize

        if not _PERSONA_PATH.exists():
            raise FileNotFoundError(f"soul.md not found at {_PERSONA_PATH}")
        self._persona_raw = _PERSONA_PATH.read_text(encoding="utf-8").strip()

        self._history:  list[dict] = []
        self._reasoning = False
        self._token_callback = None
        self._mem_queue  = queue.Queue()
        self._mem_worker = threading.Thread(target=self._mem_write_loop, daemon=True)
        self._mem_worker.start()

        self._warmup_thread = threading.Thread(target=self._warmup_llm, daemon=True)
        self._warmup_thread.start()

    def _warmup_llm(self) -> None:
        try:
            self._client.post(
                "/",
                json={
                    "model":      LLAMA_MODEL,
                    "max_tokens": 1,
                    "messages":   [{"role": "user", "content": "hi"}],
                },
            )
        except Exception as e:
            log.warning("LLM warmup failed: %s", e)

    # ── public api ────────────────────────────────────────────────────────────

    def join_warmup(self) -> None:
        if self._warmup_thread.is_alive():
            self._warmup_thread.join()

    def chat(self, user_input: str, user_id: str = _DEFAULT_USER_ID, token_callback=None) -> str:
        self._token_callback = token_callback

        # 1. retrieve relevant long-term memories
        if self._memorize:
            memories     = self._memorize.search(user_input, limit=int(os.getenv("MEMORY_RECALL_LIMIT", 5)))
            memory_block = self._memorize.format_for_context(memories)
        else:
            memories     = []
            memory_block = None

        # 2. build system prompt — persona (templated per-user) + memories
        system = _render_persona(self._persona_raw, user_id)
        if memory_block:
            system = f"{system}\n\n{memory_block}"

        # 3. tool routing — try LLM-driven tool calling first, fall back to regex
        tool_result = None
        tool_tag    = None

        history_for_check = self._sanitize_history(
            self._history[-(CONTEXT_WINDOW_TURNS * 2):] + [{"role": "user", "content": user_input}]
        )

        tool_tag, tool_result = self._try_tool_call(history_for_check, system)

        if tool_result is None:
            # fallback: regex-based intent detection (unchanged behavior)
            from core.tools import (
                is_search_intent, is_weather_intent, is_timezone_intent,
                is_currency_intent, is_joke_intent, is_anime_intent,
                extract_search_query, extract_location, extract_currency_parts,
                extract_anime_query,
                web_search_and_fetch, get_weather, get_timezone,
                get_currency, get_joke, get_anime,
            )

            if is_joke_intent(user_input):
                tool_result = get_joke()
                tool_tag    = "joke"

            elif is_weather_intent(user_input):
                location    = extract_location(user_input)
                if token_callback:
                    token_callback(f"__TOOL__:Checking weather for {location}...")
                tool_result = get_weather(location)
                tool_tag    = "weather_data"

            elif is_timezone_intent(user_input):
                location    = extract_location(user_input)
                if token_callback:
                    token_callback(f"__TOOL__:Looking up time in {location}...")
                tool_result = get_timezone(location)
                tool_tag    = "time_data"

            elif is_currency_intent(user_input):
                amount, from_cur, to_cur = extract_currency_parts(user_input)
                if token_callback:
                    token_callback(f"__TOOL__:Converting {from_cur} to {to_cur}...")
                tool_result = get_currency(amount, from_cur, to_cur)
                tool_tag    = "currency_data"

            elif is_anime_intent(user_input):
                query       = extract_anime_query(user_input)
                if token_callback:
                    token_callback(f"__TOOL__:Searching anime for {query}...")
                tool_result = get_anime(query)
                tool_tag    = "anime_data"

            elif is_search_intent(user_input):
                query       = extract_search_query(user_input)
                if token_callback:
                    token_callback(f"__SEARCHING__:{query}")
                try:
                    tool_result = web_search_and_fetch(query)
                    tool_tag    = "search_results"
                except Exception as exc:
                    log.warning("Web search failed: %s", exc)

        if tool_result and tool_tag:
            system = (
                f"{system}\n\n"
                f"<{tool_tag}>\n{tool_result}\n</{tool_tag}>\n\n"
                f"Use the above {tool_tag.replace('_', ' ')} to inform your response naturally. "
                f"Don't recite raw data — weave it into your answer as Aiko would."
            )

        # 4. wrap user turn with reasoning instruction if active
        if self._reasoning:
            prompt = (
                f"{user_input}\n\n"
                "Think through this carefully before answering. "
                "Show your reasoning inside <think> tags, then give your final answer."
            )
        else:
            prompt = user_input

        # 5. append user turn
        self._history.append({"role": "user", "content": prompt})

        # 6. trim history to context window
        trimmed = self._sanitize_history(self._history[-(CONTEXT_WINDOW_TURNS * 2):])

        # 7. LLM call
        response_text, _ = self._stream_response(trimmed, system=system)

        # 8. remove orphaned user turn on empty response
        if not response_text:
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()

        # 9. append assistant turn to history
        self._history.append({"role": "assistant", "content": response_text})

        # 10. persist to memory (background)
        self._store_async(user_input, response_text)

        # 11. auto-reset reasoning mode
        self._reasoning = False

        return response_text

    def reset_context(self) -> None:
        """Clear the in-memory conversation history for a fresh session."""
        self._history.clear()

    def last_turn(self) -> tuple[str, str] | None:
        """Return the latest complete user/assistant exchange, or None."""
        assistant_text: str | None = None
        for message in reversed(self._history):
            role    = message.get("role")
            content = (message.get("content") or "").strip()
            if not content:
                continue
            if assistant_text is None:
                if role == "assistant":
                    assistant_text = content
                continue
            if role == "user":
                return content, assistant_text
        return None

    def set_reasoning(self, enabled: bool) -> None:
        """Enable or disable reasoning mode for the next turn only."""
        self._reasoning = enabled

    def wait_for_memory(self) -> None:
        """Block until all enqueued memory writes have been persisted."""
        self._mem_queue.join()

    # ── internal ──────────────────────────────────────────────────────────────

    def _try_tool_call(self, messages: list[dict], system: str) -> tuple[str | None, str | None]:
        """
        Ask the LLM whether a tool should be called for this turn.

        Sends the conversation + tool schemas with tool_choice="auto" and a
        short max_tokens budget (this is a routing decision, not the final
        answer). If the model returns tool_calls, dispatch the first one to
        its Python implementation and return (tag, result) for context
        injection. Returns (None, None) if no tool call was made, the tool
        name/args were invalid, or the request failed for any reason — in
        which case the caller falls back to regex-based intent detection.
        """
        from core.tools import TOOL_SCHEMAS, TOOL_DISPATCH

        try:
            response = self._client.post(
                "/",
                json={
                    "model":       LLAMA_MODEL,
                    "messages":    [{"role": "system", "content": system}] + messages,
                    "tools":       TOOL_SCHEMAS,
                    "tool_choice": "auto",
                    "stream":      False,
                    "temperature": 0.2,
                    "max_tokens":  150,
                },
            )
            data = response.json()
            msg  = data.get("choices", [{}])[0].get("message", {})
            calls = msg.get("tool_calls")

            if not calls:
                return None, None

            call     = calls[0]
            name     = call.get("function", {}).get("name")
            args_raw = call.get("function", {}).get("arguments", "{}")

            if name not in TOOL_DISPATCH:
                log.warning("LLM requested unknown tool: %s", name)
                return None, None

            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
            except (ValueError, TypeError) as exc:
                log.warning("Failed to parse tool args for %s: %s (%r)", name, exc, args_raw)
                return None, None

            tag, fn = TOOL_DISPATCH[name]
            if self._token_callback:
                self._token_callback(f"__TOOL__:Calling {name}...")

            try:
                result = fn(**args)
            except Exception as exc:
                log.warning("Tool execution failed for %s: %s", name, exc)
                return None, None

            return tag, result

        except Exception as exc:
            log.warning("Tool-call attempt failed: %s", exc)
            return None, None

    def _stream_response(self, messages: list[dict], system: str = "") -> tuple[str, None]:
        num_predict = _BASE_PREDICT * _REASONING_SCALE if self._reasoning else _BASE_PREDICT

        try:
            response = self._client.post(
                "/",
                json={
                    "model":          LLAMA_MODEL,
                    "messages":       ([{"role": "system", "content": system}] + messages) if system else messages,
                    "stream":         False,
                    "temperature":    float(os.getenv("LLAMA_TEMPERATURE",    0.75)),
                    "max_tokens":     num_predict,
                    "top_p":          float(os.getenv("LLAMA_TOP_P",          0.90)),
                    "top_k":          int(os.getenv("LLAMA_TOP_K",            40)),
                    "repeat_penalty": float(os.getenv("LLAMA_REPEAT_PENALTY", 1.18)),
                    "stop":           ["<|im_end|>", "</s>", "[INST]"],
                },
            )

            data      = response.json()
            full_text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            clean_text = re.sub(r"\[?SEARCH:\s*.+?\]?", "", full_text, flags=re.IGNORECASE).strip()

            if self._token_callback and clean_text:
                self._token_callback(clean_text)

        except Exception as exc:
            msg = f"Stream failed: {exc}"
            log.error(msg)
            if self._token_callback:
                self._token_callback(f"[think] {msg}")
            return "", None

        return full_text, None

    def _sanitize_history(self, messages: list[dict]) -> list[dict]:
        """Enforce strict user/assistant alternation."""
        if not messages:
            return []
        sanitized = [messages[0]]
        for msg in messages[1:]:
            if msg["role"] == sanitized[-1]["role"]:
                sanitized[-1] = msg
            else:
                sanitized.append(msg)
        while sanitized and sanitized[0]["role"] != "user":
            sanitized.pop(0)
        return sanitized

    def _store_async(self, user_input: str, response_text: str) -> None:
        self._mem_queue.put((user_input, response_text))

    def _mem_write_loop(self) -> None:
        """Serial background worker that drains the memory write queue."""
        while True:
            user_input, response_text = self._mem_queue.get()
            try:
                if self._memorize:
                    self._memorize.add([
                        {"role": "user",      "content": user_input[:500]},
                        {"role": "assistant", "content": response_text[:800]},
                    ])
            except Exception as exc:
                log.error("Async memory write failed: %s", exc)
            finally:
                self._mem_queue.task_done()