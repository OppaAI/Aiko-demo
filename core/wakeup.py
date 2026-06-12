"""
core/wakeup.py
Aiko's boot orchestrator — owns parallel subsystem startup and warmup sequencing.
main.py calls AikoWakeup().boot(...) and receives a BootResult with all live
subsystem references; it never needs to know the startup choreography.
Progress is reported through three injected callbacks so wakeup.py stays
completely TUI-ignorant:
    on_loading(key)  — subsystem is starting
    on_done(key)     — subsystem finished successfully
    on_skip(key)     — subsystem skipped
Each module owns its BOOT_LABELS dict; wakeup collects them and exposes
ALL_BOOT_LABELS so the UI can register display text before boot begins.
Usage:
    result = AikoWakeup().boot(
        on_loading = ...,
        on_done    = ...,
        on_skip    = ...,
    )
    think    = result.think
    memorize = result.memorize
Note: TTS and ASR subsystems are not used in Gradio/HF Space deployments.
      Gradio handles audio I/O via gr.Audio; speak and listen are always None.
"""

import threading
from dataclasses import dataclass
from typing import Callable
from core.log import get_logger
log = get_logger(__name__)

from core.think    import BOOT_LABELS as _THINK_LABELS
from core.memorize import BOOT_LABELS as _MEM_LABELS

# ── result container ──────────────────────────────────────────────────────────

@dataclass
class BootResult:
    """Holds all live subsystem references produced during boot."""
    think:    object        # AikoThink
    memorize: object        # AikoMemorize
    speak:    None = None   # Not used in Gradio deployment
    listen:   None = None   # Not used in Gradio deployment


# ── wakeup ────────────────────────────────────────────────────────────────────

class AikoWakeup:
    """
    Parallel boot orchestrator for Aiko cognitive subsystems.
    Boots AikoThink and AikoMemorize concurrently with granular progress
    reporting per step.
    TTS and ASR subsystems are excluded — Gradio handles audio I/O natively
    via gr.Audio, so speak/listen are always None.
    Each subsystem owns its BOOT_LABELS; ALL_BOOT_LABELS merges them so
    the UI can register display text before boot begins.
    """

    ALL_BOOT_LABELS: dict[str, str] = {
        **_THINK_LABELS,
        **_MEM_LABELS,
    }

    def boot(
        self,
        on_loading: Callable[[str], None],
        on_done:    Callable[[str], None],
        on_skip:    Callable[[str], None],
    ) -> BootResult:
        """
        Execute boot sequence and return live subsystem references.
        Parallel phase: AikoThink + AikoMemorize boot concurrently.
        Memory backend is injected into think once both are ready.
        Args:
            on_loading: Called with a progress key when a subsystem starts.
            on_done:    Called with a progress key when a subsystem finishes.
            on_skip:    Called with a progress key when a subsystem is skipped.
        Returns:
            BootResult with think and memorize references; speak and listen
            are always None.
        """
        from core.memorize import AikoMemorize
        from core.think    import AikoThink

        memorize  = [None]
        think_ref = [None]
        mem_ready = threading.Event()

        # ── parallel boot ─────────────────────────────────────────────────────

        def init_think():
            on_loading('think_start')
            think_ref[0] = AikoThink(None, speak=None)
            on_done('think_start')
            on_loading('think_warmup')
            think_ref[0].join_warmup()
            on_done('think_warmup')
            mem_ready.wait()                       # hold until memorize is ready
            think_ref[0]._memorize = memorize[0]   # inject memory backend

        def init_memorize():
            try:
                on_loading('mem_sqlite_vec')
                memorize[0] = AikoMemorize(silent=True)
                on_done('mem_sqlite_vec')
                on_loading('mem_embed')
                on_done('mem_embed')
                on_loading('mem_cleanup')
                memorize[0].cleanup()
                on_done('mem_cleanup')
                on_loading('mem_ready')
                on_done('mem_ready')
            except Exception as e:
                log.error("Memory boot failed: %s", e)
            finally:
                mem_ready.set()  # always unblock init_think, even on failure
            if memorize[0] is None:
                return
            from core.dream import start as start_dream_scheduler
            start_dream_scheduler(memorize[0])

        t1 = threading.Thread(target=init_think,    daemon=True)
        t2 = threading.Thread(target=init_memorize, daemon=True)
        t1.start(); t2.start()
        t1.join();  t2.join()

        on_skip('speak_skip')
        on_skip('listen_skip')

        return BootResult(
            think    = think_ref[0],
            memorize = memorize[0],
        )