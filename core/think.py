"""
core/think.py

Aiko's cognitive loop.
  - Retrieves relevant memories before each turn
  - Proactive intent gate: detects data-seeking queries and injects live
    web search results into the system prompt BEFORE the LLM speaks
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

LLAMA_BASE_URL      = os.getenv("LLAMA_BASE_URL", "http://localhost:11434")
LLAMA_MODEL         = os.getenv("LLAMA_MODEL",    "ministral-3:3b-instruct-2512-q4_K_M")
GROQ_BASE_URL       = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL          = os.getenv("GROQ_MODEL",    "llama-3.1-8b-instant")
CONTEXT_WINDOW_TURNS = int(os.getenv("CONTEXT_WINDOW_TURNS", 20))

_BASE_PREDICT    = 400   # normal token budget per turn
_REASONING_SCALE = 3     # multiplier applied to num_predict in reasoning mode

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

# question words / phrases that strongly imply the user wants live data
_INTENT_QUESTION_WORDS = re.compile(
    r"\b(what(?:'s| is| are| was| were)?"
    r"|who(?:'s| is| are)?"
    r"|when(?:'s| is| are| was| were)?"
    r"|where(?:'s| is| are)?"
    r"|how (?:much|many|old|tall|long|far|do|does|did|is|are|was|were)"
    r"|why (?:is|are|was|were|did|does|do)"
    r"|price of|cost of|worth of"
    r"|latest|recent|current|today|tonight|this week|this month|right now|live"
    r"|news|update|score|weather|forecast|stock|crypto|rate|ranking|standings"
    r"|release date|out now|available|coming out"
    r")\b",
    re.IGNORECASE,
)

# explicit data-request phrases — override everything
_INTENT_EXPLICIT = re.compile(
    r"\b(search for|look up|find out|tell me about|what do you know about"
    r"|google|check online|check the web)\b",
    re.IGNORECASE,
)

# topics that are always stale in a model's weights — force search
_INTENT_STALENESS = re.compile(
    r"\b(weather|temperature|forecast|rain|snow|wind"
    r"|score|standings|game|match|result|winner"
    r"|stock|crypto|bitcoin|price|market|nasdaq|s&p"
    r"|news|breaking|headline|election|vote"
    r"|release|launch|update|version|patch)\b",
    re.IGNORECASE,
)


def _is_data_intent(text: str) -> bool:
    """
    Return True when the user's message likely requires live or recent data.

    Combines three signals: explicit lookup phrases, staleness keywords, and
    question words. Any single signal is sufficient to trigger a search.
    Short conversational inputs (< 4 words) are skipped to avoid false positives.
    """
    if len(text.split()) < 4:
        return False  # too short to be a genuine data query
    if _INTENT_EXPLICIT.search(text):
        return True
    if _INTENT_STALENESS.search(text):
        return True
    if _INTENT_QUESTION_WORDS.search(text):
        return True
    return False


def _build_search_query(text: str) -> str:
    """
    Derive a clean search query from user input.

    Strips common conversational lead-ins so SearXNG gets a tight query
    rather than a full sentence with filler words.
    """
    filler = re.compile(
        r"^(hey aiko[,.]?\s*|aiko[,.]?\s*|can you\s*|could you\s*"
        r"|please\s*|tell me\s*|what(?:'s| is)\s*|do you know\s*"
        r"|search for\s*|look up\s*|find\s*)",
        re.IGNORECASE,
    )
    return filler.sub("", text).strip()


# ── think ─────────────────────────────────────────────────────────────────────

class AikoThink:
    """
    Aiko's conversational core.
    speak is injected pre-warmed from wakeup.py.
    LLM warmup starts immediately on init in a background thread.
    wakeup.py calls join_warmup() to block until the model is hot.
    """

    def __init__(self, memorize: AikoMemorize, speak: AikoSpeak | None = None) -> None:
        """
        Initialise the cognitive loop.

        Starts the LLM warmup and memory-write worker threads immediately so
        both are ready before the first user prompt arrives.

        Args:
            memorize: Injected memory backend for retrieval and persistence.
                      May be None at construction time — wakeup.py injects it
                      after memorize boot completes via think._memorize = ...
            speak:    Pre-warmed TTS backend; pass None to run silent.
        """
        self._client = httpx.Client(
            base_url=LLAMA_BASE_URL,
            timeout=120.0,
        )
        #self._client = httpx.Client(
        #    base_url=GROQ_BASE_URL,
        #    timeout=120.0,
        #    headers={"Authorization": f"Bearer {os.getenv('GROQ_API_KEY', '')}"},
        #)
                
        self._memorize  = memorize
        self._speak     = speak
        self._persona   = _load_persona()
        self._history:  list[dict] = []
        self._reasoning = False        # reasoning mode off by default; toggled by /think
        self._mem_queue  = queue.Queue()
        self._mem_worker = threading.Thread(target=self._mem_write_loop, daemon=True)
        self._mem_worker.start()

        self._warmup_thread = threading.Thread(target=self._warmup_llm, daemon=True)
        self._warmup_thread.start()

    def _warmup_llm(self) -> None:
        try:
            self._client.post(
                # ── llama.cpp on Modal ───
                "/",
                # ── Groq ────────────────
            #    "/v1/chat/completions",
                json={
                    # ── llama.cpp ────────
                    "model":    LLAMA_MODEL,
                    "n_predict": 1,
                    # ── Groq ─────────────
            #        "model":                 GROQ_MODEL,
                    #"max_completion_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                    "stream":   False,
                },
            )
        except Exception as e:
            log.warning("LLM warmup failed: %s", e)

    # ── public api ────────────────────────────────────────────────────────────

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

        # 4. proactive search gate — inject live results BEFORE the LLM speaks
        #    soul.md already instructs Aiko to treat <search_results> as her
        #    sole source for that topic; no extra prompt wording needed here.
        if _is_data_intent(user_input):
            query = _build_search_query(user_input)
            log.debug("Search intent detected — querying: %s", query)

            if token_callback:
                token_callback(f"__SEARCHING__:{query}")

            try:
                from core.tools import web_search
                results = web_search(query)
            except Exception as exc:
                results = f"[search failed: {exc}]"
                log.warning("Web search failed: %s", exc)

            system = f"{system}\n\n<search_results>\n{results}\n</search_results>"

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
        """
        Return the latest complete user/assistant exchange, if one exists.

        Walks history in reverse to find the most recent assistant reply and
        its paired user message.

        Returns:
            (user_text, assistant_text) for the last turn, or None if the
            history contains no complete exchange yet.
        """
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
        """
        Enable or disable reasoning mode for the next turn only.

        When enabled, chat() wraps the user prompt with a step-by-step
        instruction and triples num_predict to budget for the <think>
        scratchpad. Auto-resets to False after each chat() call — single-shot
        by design so a forgotten /think never bleeds into normal conversation.

        Args:
            enabled: True to activate reasoning for the next turn, False to cancel.
        """
        self._reasoning = enabled

    def set_speak(self, speak) -> None:
        """Hot-swap the TTS backend. Pass None to silence, speak instance to restore."""
        self._speak = speak

    def wait_for_memory(self) -> None:
        """Block until all enqueued memory writes have been persisted."""
        self._mem_queue.join()

    # ── internal ──────────────────────────────────────────────────────────────

    def _stream_response(self, messages: list[dict], system: str = "") -> tuple[str, str | None]:
        """Returns (response_text, search_query | None)"""
        full_response    = []
        buffer           = ""
        is_searching     = False
        buffering_active = True
        num_predict      = _BASE_PREDICT * _REASONING_SCALE if self._reasoning else _BASE_PREDICT
    
        try:
            import json
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
                # ── Groq ─────────────────────────────────────────────────────
                #json={
                #    "model":                 GROQ_MODEL,
                #    "messages":              ([{"role": "system", "content": system}] + messages) if system else messages,
                #    "stream":                False,
                #    "temperature":           float(os.getenv("LLAMA_TEMPERATURE", 0.75)),
                #    "max_completion_tokens": num_predict,
                #    "top_p":                 float(os.getenv("LLAMA_TOP_P", 0.90)),
                #    "stop":                  None,
                #},
            )
            
            data      = response.json()
            full_text = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
        
            # check for search tag in full response (with or without brackets)
            match = re.search(r"\[SEARCH:\s*(.+?)\]", full_text, re.IGNORECASE)
            if match:
                return "", match.group(1).strip()
        
            # strip any leaked search tags before display
            clean_text = re.sub(r"\[?SEARCH:\s*.+?\]?", "", full_text, flags=re.IGNORECASE).strip()
        
            # no search tag — send to callback
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
        """
        Enforce strict user/assistant alternation.
        Merges consecutive same-role messages (keeps last).
        Strips leading assistant turns — history must start with user.
        """
        if not messages:
            return []

        sanitized = [messages[0]]
        for msg in messages[1:]:
            if msg["role"] == sanitized[-1]["role"]:
                sanitized[-1] = msg   # keep the later one
            else:
                sanitized.append(msg)

        # must start with user — strip any leading assistant orphans
        while sanitized and sanitized[0]["role"] != "user":
            sanitized.pop(0)

        return sanitized

    def _store_async(self, user_input: str, response_text: str) -> None:
        """
        Enqueue a completed turn for background memory persistence.

        Non-blocking — the chat path returns immediately after this call.
        The background worker in _mem_write_loop drains the queue serially.

        Args:
            user_input:    The user's raw message for this turn.
            response_text: The assistant's full response for this turn.
        """
        self._mem_queue.put((user_input, response_text))

    def _mem_write_loop(self) -> None:
        """
        Serial background worker that drains the memory write queue.

        Runs for the lifetime of the process (daemon thread). Processes writes
        in order so memory entries are never interleaved or lost.
        """
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