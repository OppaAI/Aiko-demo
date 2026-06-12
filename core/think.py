"""
core/think.py

Aiko's cognitive loop.
  - Retrieves relevant memories before each turn
  - Explicit search gate: fires ONLY when user asks Aiko to search the web
  - Streams LLM response via token_callback
  - Stores the turn into long-term memory after each response (background thread)
  - Supports single-shot reasoning mode via set_reasoning(True) / /think command
"""

import os
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

LLAMA_BASE_URL       = os.getenv("LLAMA_BASE_URL",       "https://your-modal-endpoint.modal.run")
LLAMA_MODEL          = os.getenv("LLAMA_MODEL",           "meta-llama/Llama-3.1-8B-Instruct")
LLAMA_API_KEY        = os.getenv("LLAMA_API_KEY",         "")
CONTEXT_WINDOW_TURNS = int(os.getenv("CONTEXT_WINDOW_TURNS", 20))

_BASE_PREDICT    = 400   # normal token budget per turn
_REASONING_SCALE = 3     # multiplier applied in reasoning mode

_PERSONA_PATH = Path(__file__).resolve().parent.parent / "persona" / "soul.md"


def _load_persona() -> str:
    """Read and return the persona definition from soul.md."""
    if not _PERSONA_PATH.exists():
        raise FileNotFoundError(f"soul.md not found at {_PERSONA_PATH}")
    persona = _PERSONA_PATH.read_text(encoding="utf-8").strip()
    user_id = os.getenv("USER_ID", "OppaAI")
    today   = datetime.now().strftime("%B %d, %Y")
    return persona.replace("USER_ID_HERE", user_id).replace("TODAY_HERE", today)


# ── search intent gate ────────────────────────────────────────────────────────

_SEARCH_TRIGGERS = re.compile(
    r"\b(check (?:the )?internet|search (?:the )?web|look it up|go online|"
    r"search online|check online|look online|google that|browse for|"
    r"fetch.*web|web search|internet search)\b",
    re.IGNORECASE,
)

_LEADING_JUNK = re.compile(r"^[\s,;.\-—–]+")

_LEADING_FILLER = re.compile(
    r"^("
    r"and\s+|but\s+|then\s+|so\s+|for\s+"
    r"|hey aiko[,.]?\s*|aiko[,.]?\s*"
    r"|can you\s*|could you\s*|please\s*|me\s+"
    r"|tell me\s*|give me\s*|show me\s*|get me\s*"
    r"|find\s+(?:out\s+)?|look\s+(?:up\s+)?"
    r"|(?:some\s+)?(?:detailed?\s+)?info(?:rmation)?\s+(?:about\s+|on\s+)?"
    r"|(?:more\s+)?details?\s+(?:about\s+|on\s+)?"
    r"|about\s+"
    r")",
    re.IGNORECASE,
)


def _is_data_intent(text: str) -> bool:
    """Return True only when the user explicitly asks Aiko to search the web."""
    return bool(_SEARCH_TRIGGERS.search(text.strip()))


def _build_search_query(text: str) -> str:
    """Strip trigger phrase + conversational filler, leaving a clean DDG query."""
    cleaned = _SEARCH_TRIGGERS.sub("", text).strip()
    prev = None
    while prev != cleaned:
        prev    = cleaned
        cleaned = _LEADING_JUNK.sub("", cleaned).strip()
        cleaned = _LEADING_FILLER.sub("", cleaned).strip()
    return cleaned or text.strip()


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
        self._persona   = _load_persona()
        self._history:  list[dict] = []
        self._reasoning = False
        self._mem_queue  = queue.Queue()
        self._mem_worker = threading.Thread(target=self._mem_write_loop, daemon=True)
        self._mem_worker.start()

        self._warmup_thread = threading.Thread(target=self._warmup_llm, daemon=True)
        self._warmup_thread.start()

    def _warmup_llm(self) -> None:
        try:
            self._client.post(
                "/chat/completions",
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
        """
        Block until the background LLM warmup thread completes.
        Called by wakeup.py after boot so the first real request hits a hot model.
        """
        if self._warmup_thread.is_alive():
            self._warmup_thread.join()

    def chat(self, user_input: str, token_callback=None) -> str:
        self._token_callback = token_callback

        # 1. retrieve relevant long-term memories
        if self._memorize:
            memories     = self._memorize.search(user_input, limit=int(os.getenv("MEMORY_RECALL_LIMIT", 5)))
            memory_block = self._memorize.format_for_context(memories)
        else:
            memories     = []
            memory_block = None

        # 2. build system prompt — persona + memories
        system = self._persona
        if memory_block:
            system = f"{system}\n\n{memory_block}"

        # 3. explicit search gate — only fires when user asks Aiko to search
        if _is_data_intent(user_input):
            query = _build_search_query(user_input)
            log.debug("Search intent detected — querying: %s", query)

            if token_callback:
                token_callback(f"__SEARCHING__:{query}")

            try:
                from core.tools import web_search_and_fetch
                results = web_search_and_fetch(query)

                system = (
                    f"{system}\n\n"
                    f"<search_results>\n{results}\n</search_results>\n\n"
                    "IMPORTANT: Answer using ONLY the search results above. "
                    "Do not use your training data for this topic. "
                    "If the answer is in the results, state it directly."
                )
            except Exception as exc:
                log.warning("Web search failed: %s", exc)

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

        # 10. persist to memory (background) — store original input, not wrapped prompt
        self._store_async(user_input, response_text)

        # 11. auto-reset reasoning mode — single-shot per /think invocation
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

    def _stream_response(self, messages: list[dict], system: str = "") -> tuple[str, None]:
        num_predict = _BASE_PREDICT * _REASONING_SCALE if self._reasoning else _BASE_PREDICT

        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model":            LLAMA_MODEL,
                    "messages":         ([{"role": "system", "content": system}] + messages) if system else messages,
                    "stream":           False,
                    "temperature":      float(os.getenv("LLAMA_TEMPERATURE",    0.75)),
                    "max_tokens":       num_predict,
                    "top_p":            float(os.getenv("LLAMA_TOP_P",          0.90)),
                    "top_k":            int(os.getenv("LLAMA_TOP_K",            40)),
                    "repeat_penalty":   float(os.getenv("LLAMA_REPEAT_PENALTY", 1.18)),
                    "stop":             ["<|im_end|>", "</s>", "[INST]"],
                },
            )

            data      = response.json()
            full_text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

            # strip any leaked search tags (defensive)
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
        """Enqueue a completed turn for background memory persistence."""
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