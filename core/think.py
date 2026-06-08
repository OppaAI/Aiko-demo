"""
core/think.py

Aiko's cognitive loop.
  - Retrieves relevant memories before each turn
  - Explicit search gate: fires ONLY when user asks Aiko to search the web
  - Streams LLM response to console + TTS simultaneously
  - Stores the turn into long-term memory after each response (background thread)
  - Supports single-shot reasoning mode via set_reasoning(True) / /think command
"""

import logging
import os
import warnings

warnings.filterwarnings("ignore")
logging.getLogger("phonemizer").setLevel(logging.ERROR)
logging.getLogger("torch").setLevel(logging.ERROR)
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from datetime import datetime
import httpx
from pathlib import Path
import queue
import re
import threading

from core.memorize import AikoMemorize
from core.speak    import AikoSpeak
from core.log      import get_logger

log = get_logger(__name__)

# ── boot labels ───────────────────────────────────────────────────────────────

BOOT_LABELS = {
    'think_start':  'Loading LLM client + persona...',
    'think_warmup': 'Warming up language model...',
}

# ── config ────────────────────────────────────────────────────────────────────

LLAMA_BASE_URL       = os.getenv("LLAMA_BASE_URL", "http://localhost:11434")
LLAMA_MODEL          = os.getenv("LLAMA_MODEL",    "ministral-3:3b-instruct-2512-q4_K_M")
GROQ_BASE_URL        = os.getenv("GROQ_BASE_URL",  "https://api.groq.com/openai/v1")
GROQ_MODEL           = os.getenv("GROQ_MODEL",     "llama-3.1-8b-instant")
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

# Fires only on explicit user commands to search the web.
_SEARCH_TRIGGERS = re.compile(
    r"\b(check (?:the )?internet|search (?:the )?web|look it up|go online|"
    r"search online|check online|look online|google that|browse for|"
    r"fetch.*web|web search|internet search)\b",
    re.IGNORECASE,
)


def _is_data_intent(text: str) -> bool:
    """Return True only when the user explicitly asks Aiko to search the web."""
    return bool(_SEARCH_TRIGGERS.search(text.strip()))


def _build_search_query(text: str) -> str:
    """Strip trigger phrase + conversational filler, extract clean topic."""
    # remove the trigger phrase first
    cleaned = _SEARCH_TRIGGERS.sub("", text).strip()
    # strip leading conjunctions/filler left behind after trigger removal
    cleaned = re.sub(
        r"^(and\s+|but\s+|then\s+|so\s+|,\s*)+",
        "", cleaned, flags=re.IGNORECASE
    ).strip()
    # strip conversational lead-ins
    filler = re.compile(
        r"^(hey aiko[,.]?\s*|aiko[,.]?\s*|can you\s*|could you\s*|"
        r"please\s*|for\s+me\s*|tell me\s*|give me\s*|"
        r"(detail(?:ed)?\s+)?info(?:rmation)?\s+about\s*)",
        re.IGNORECASE,
    )
    # apply filler strip repeatedly until stable
    prev = None
    while prev != cleaned:
        prev = cleaned
        cleaned = filler.sub("", cleaned).strip()
    return cleaned or text.strip()

# ── think ─────────────────────────────────────────────────────────────────────

class AikoThink:
    """
    Aiko's conversational core.
    speak is injected pre-warmed from wakeup.py.
    LLM warmup starts immediately on init in a background thread.
    wakeup.py calls join_warmup() to block until the model is hot.
    """

    def __init__(self, memorize: AikoMemorize, speak: AikoSpeak | None = None) -> None:
        self._client = httpx.Client(
            base_url=LLAMA_BASE_URL,
            timeout=120.0,
        )
        self._memorize  = memorize
        self._speak     = speak
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
                "/",
                json={
                    "model":     LLAMA_MODEL,
                    "n_predict": 1,
                    "messages":  [{"role": "user", "content": "hi"}],
                    "stream":    False,
                },
            )
        except Exception as e:
            log.warning("LLM warmup failed: %s", e)

    # ── public api ────────────────────────────────────────────────────────────

    def join_warmup(self) -> None:
        """
        Block until the background LLM warmup thread completes.
        Called by wakeup.py after boot so the first real request hits a hot model.
        Safe to call multiple times — joining a finished thread is a no-op.
        """
        if self._warmup_thread.is_alive():
            self._warmup_thread.join()

    def chat(self, user_input: str, token_callback=None) -> str:
        self._token_callback = token_callback

        # 1. interrupt any ongoing speech before processing new input
        if self._speak and self._speak.is_playing():
            self._speak.stop()

        # 2. retrieve relevant long-term memories
        if self._memorize:
            memories     = self._memorize.search(user_input, limit=int(os.getenv("MEMORY_RECALL_LIMIT", 5)))
            memory_block = self._memorize.format_for_context(memories)
        else:
            memories     = []
            memory_block = None

        # 3. build system prompt — persona + memories
        system = self._persona
        if memory_block:
            system = f"{system}\n\n{memory_block}"

        # 4. explicit search gate — only fires when user asks Aiko to search
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

        # 5. wrap user turn with reasoning instruction if active
        if self._reasoning:
            prompt = (
                f"{user_input}\n\n"
                "Think through this carefully before answering. "
                "Show your reasoning inside <think> tags, then give your final answer."
            )
        else:
            prompt = user_input

        # 6. append user turn
        self._history.append({"role": "user", "content": prompt})

        # 7. trim history to context window
        trimmed = self._sanitize_history(self._history[-(CONTEXT_WINDOW_TURNS * 2):])

        # 8. single LLM call — search results already in system prompt if needed
        response_text, _ = self._stream_response(trimmed, system=system)

        # 9. remove orphaned user turn on empty response
        if not response_text:
            if self._history and self._history[-1]["role"] == "user":
                self._history.pop()

        # 10. append assistant turn to history
        self._history.append({"role": "assistant", "content": response_text})

        # 11. persist to memory (background) — store original input, not wrapped prompt
        self._store_async(user_input, response_text)

        # 12. auto-reset reasoning mode — single-shot per /think invocation
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

    def set_speak(self, speak) -> None:
        """Hot-swap the TTS backend. Pass None to silence, speak instance to restore."""
        self._speak = speak

    def wait_for_memory(self) -> None:
        """Block until all enqueued memory writes have been persisted."""
        self._mem_queue.join()

    # ── internal ──────────────────────────────────────────────────────────────

    def _stream_response(self, messages: list[dict], system: str = "") -> tuple[str, str | None]:
        """Returns (response_text, None). Search tag emission is no longer used."""
        num_predict = _BASE_PREDICT * _REASONING_SCALE if self._reasoning else _BASE_PREDICT

        try:
            response = self._client.post(
                "/",
                json={
                    "model":          LLAMA_MODEL,
                    "messages":       ([{"role": "system", "content": system}] + messages) if system else messages,
                    "stream":         False,
                    "temperature":    float(os.getenv("LLAMA_TEMPERATURE", 0.75)),
                    "max_tokens":     num_predict,
                    "top_p":          float(os.getenv("LLAMA_TOP_P", 0.90)),
                    "top_k":          int(os.getenv("LLAMA_TOP_K", 40)),
                    "repeat_penalty": float(os.getenv("LLAMA_REPEAT_PENALTY", 1.18)),
                    "stop":           ["<|im_end|>", "</s>", "[INST]"],
                },
            )

            data      = response.json()
            full_text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""

            # strip any leaked search tags (defensive — LLM should no longer emit them)
            clean_text = re.sub(r"\[?SEARCH:\s*.+?\]?", "", full_text, flags=re.IGNORECASE).strip()

            if self._token_callback and clean_text:
                self._token_callback(clean_text)
            else:
                print(f"\nAiko-chan: {clean_text}")

            if self._speak and full_text:
                self._speak.feed(full_text)
                self._speak.play_async()

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
                log.error(f"Async memory write failed: {exc}")
            finally:
                self._mem_queue.task_done()