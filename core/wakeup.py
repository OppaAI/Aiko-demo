"""
core/wakeup.py (CLEANED VERSION)

Aiko boot orchestrator — minimal, stable, Gradio-safe.

This version removes unused voice pipeline (listen/speak warmup)
and focuses only on:
    - think (LLM brain)
    - memorize (memory backend)

Designed for:
    - stable HF Spaces / Gradio lifecycle
    - no partial initialization leaks
    - no unused subsystem overhead
"""

import threading
from dataclasses import dataclass
from typing import Callable
from core.log import get_logger

log = get_logger(__name__)

from core.think import BOOT_LABELS as _THINK_LABELS
from core.memorize import BOOT_LABELS as _MEM_LABELS


# ─────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────

@dataclass
class BootResult:
    think: object
    memorize: object


# ─────────────────────────────────────────────
# STATE
# ─────────────────────────────────────────────

@dataclass
class _BootState:
    think: object | None = None
    memorize: object | None = None


# ─────────────────────────────────────────────
# WAKEUP
# ─────────────────────────────────────────────

class AikoWakeup:
    """
    Minimal boot orchestrator.

    Only boots:
        - AikoThink
        - AikoMemorize

    Everything else (TTS, ASR) is external runtime concern.
    """

    ALL_BOOT_LABELS: dict[str, str] = {
        **_THINK_LABELS,
        **_MEM_LABELS,
    }

    def __init__(self, text_mode: bool = False) -> None:
        self._text_mode = text_mode

    def boot(
        self,
        on_loading: Callable[[str], None],
        on_done: Callable[[str], None],
        on_skip: Callable[[str], None],
    ) -> BootResult:

        from core.memorize import AikoMemorize
        from core.think import AikoThink

        state = _BootState()
        ready = threading.Event()

        # ── THINK ───────────────────────────────
        def init_think():
            on_loading("think_start")
            state.think = AikoThink(None)
            on_done("think_start")

            on_loading("think_warmup")
            state.think.join_warmup()
            on_done("think_warmup")

            ready.wait()
            state.think._memorize = state.memorize

        # ── MEMORIZE ────────────────────────────
        def init_memorize():
            try:
                on_loading("mem_init")
                state.memorize = AikoMemorize(silent=True)
                on_done("mem_init")

                on_loading("mem_ready")
                on_done("mem_ready")

            except Exception as e:
                log.error("Memory boot failed: %s", e)

            finally:
                ready.set()

        # ── PARALLEL BOOT ────────────────────────
        t1 = threading.Thread(target=init_think, daemon=True)
        t2 = threading.Thread(target=init_memorize, daemon=True)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        return BootResult(
            think=state.think,
            memorize=state.memorize,
        )