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

Note: the dream scheduler is not used in this Gradio/HF Space demo, so
      `speak` is always None. ASR (`listen`) IS used here — browser-recorded
      audio is transcribed via ui.listen.transcribe_file (Modal endpoint
      or local faster-whisper fallback) — but it has no persistent live
      object to hand back, so `listen` remains None in BootResult; its
      warmup is just a cold-start prefill (see _warmup_asr).

All four warmups (LLM, TTS, ASR, plus think/memorize init) fire real
inference/synthesis/transcription requests rather than health checks, so
CUDA kernels and Modal containers are hot before the first real user turn.
"""

import os
import time
import threading
from dataclasses import dataclass
from pathlib import Path
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
    listen:   None = None   # No persistent object; see ui.listen.transcribe_file


# ── warmup helpers ────────────────────────────────────────────────────────────

def _warmup_llm(
    on_loading: Callable[[str], None],
    on_done:    Callable[[str], None],
    on_skip:    Callable[[str], None],
) -> None:
    """
    Proper LLM warmup:
      Run a real inference request with the actual soul.md system prompt
      so CUDA kernels are initialized and the system prompt prefix is
      hot in the KV cache — first real user turn will be much faster.
      No /health gate: the inference POST itself rides out a cold Modal
      container start.
    """
    import httpx

    base_url = os.getenv("LLAMA_BASE_URL", "").rstrip("/")
    if not base_url:
        log.debug("LLAMA_BASE_URL not set — skipping LLM warmup")
        on_skip("warmup_llm")
        return

    on_loading("warmup_llm")

    soul_path = Path(__file__).resolve().parent.parent / "persona" / "soul.md"
    try:
        system_prompt = soul_path.read_text(encoding="utf-8").strip() if soul_path.exists() else "You are Aiko."
    except Exception:
        system_prompt = "You are Aiko."

    # Replace template vars with neutral placeholders for warmup
    system_prompt = system_prompt.replace("USER_ID_HERE", "Guest").replace("TODAY_HERE", "today")

    try:
        r = httpx.post(
            base_url,  # /chat endpoint
            json={
                "model":       os.getenv("LLAMA_MODEL", "aiko"),
                "messages":    [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": "hi"},
                ],
                "max_tokens":  16,    # just enough to force a full forward pass
                "temperature": 0.1,
            },
            timeout=180,  # cold Modal container can take a while to spin up
        )
        log.info("LLM warmup inference: status=%s", r.status_code)
        if r.status_code == 200:
            on_done("warmup_llm")
        else:
            log.warning("LLM warmup got non-200: %s %s", r.status_code, r.text[:200])
            on_skip("warmup_llm")
    except Exception as e:
        log.warning("LLM warmup inference failed (non-fatal): %s", e)
        on_skip("warmup_llm")


def _warmup_tts(
    on_loading: Callable[[str], None],
    on_done:    Callable[[str], None],
    on_skip:    Callable[[str], None],
) -> None:
    """
    Proper TTS warmup:
      Run a real synthesis request so the inner llama-server inside
      MioTTS initializes CUDA kernels and codec generation paths.
      No /health gate: the synthesis POST itself rides out a cold
      Modal container start.
    """
    import httpx

    url = os.getenv("MIOTTS_URL", "").rstrip("/")
    if not url:
        log.debug("MIOTTS_URL not set — skipping TTS warmup")
        on_skip("warmup_tts")
        return

    on_loading("warmup_tts")

    preset_id = os.getenv("MIOTTS_PRESET", "aiko_voice")
    try:
        r = httpx.post(
            f"{url}/synthesize",
            json={"text": "Hello.", "preset_id": preset_id},
            timeout=180,  # cold Modal container can take a while to spin up
        )
        log.info("TTS warmup synthesis: status=%s bytes=%d", r.status_code, len(r.content))
        if r.status_code == 200:
            on_done("warmup_tts")
        else:
            log.warning("TTS warmup got non-200: %s %s", r.status_code, r.text[:200])
            on_skip("warmup_tts")
    except Exception as e:
        log.warning("TTS warmup synthesis failed (non-fatal): %s", e)
        on_skip("warmup_tts")


def _warmup_asr(
    on_loading: Callable[[str], None],
    on_done:    Callable[[str], None],
    on_skip:    Callable[[str], None],
) -> None:
    """
    Proper ASR warmup:
      Run a real transcription on a short silent WAV so faster-whisper
      (Modal large-v3-turbo via AIKO_ASR_URL, or local CTranslate2
      fallback) has its CUDA kernels initialized before the first real
      user utterance — avoids a multi-second stall on turn 1.
      No /health gate: the transcription request itself rides out a
      cold Modal container start.
    """
    import wave
    import struct
    import tempfile

    from ui.listen import ASR_URL, transcribe_file

    on_loading("warmup_asr")

    # ~0.5s of silence at 16kHz mono — enough to drive a full forward
    # pass through the encoder/decoder without needing real speech.
    sample_rate = 16000
    num_samples = sample_rate // 2
    silence = struct.pack("<" + "h" * num_samples, *([0] * num_samples))

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(silence)

        if ASR_URL:
            import httpx
            with open(tmp_path, "rb") as f:
                resp = httpx.post(
                    f"{ASR_URL}/transcribe",
                    files={"audio": ("warmup.wav", f, "audio/wav")},
                    timeout=180,  # cold Modal container can take a while to spin up
                )
            resp.raise_for_status()
            log.info("ASR warmup (Modal): status=%s", resp.status_code)
        else:
            text = transcribe_file(tmp_path)
            log.info("ASR warmup (local): transcript=%r", text)

        on_done("warmup_asr")
    except Exception as e:
        log.warning("ASR warmup failed (non-fatal): %s", e)
        on_skip("warmup_asr")
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ── wakeup ────────────────────────────────────────────────────────────────────

class AikoWakeup:
    """
    Parallel boot orchestrator for Aiko cognitive subsystems.
    Boots AikoThink, AikoMemorize, and the LLM/TTS/ASR Modal servers
    concurrently with granular progress reporting per step.
    Dream scheduler is excluded from this demo deployment.
    Modal server warmups (LLM + TTS + ASR) fire immediately and run in
    parallel with think/memorize init so boot time is minimized.
    """

    ALL_BOOT_LABELS: dict[str, str] = {
        **_THINK_LABELS,
        **_MEM_LABELS,
        "warmup_llm": "🧠 Waking LLM server...",
        "warmup_tts": "🔊 Waking voice server...",
        "warmup_asr": "🎙️ Waking ear...",
        "speak_skip": "TTS skipped (cloud mode)",
        "listen_skip": "ASR skipped (cloud mode)",
    }

    def boot(
        self,
        on_loading: Callable[[str], None],
        on_done:    Callable[[str], None],
        on_skip:    Callable[[str], None],
    ) -> BootResult:
        """
        Execute boot sequence and return live subsystem references.

        All five subsystems boot concurrently:
          - AikoThink          (LLM client + persona load + internal warmup)
          - AikoMemorize       (sqlite-vec + fastembed + cleanup)
          - Modal LLM warmup   (real inference prefill)
          - Modal TTS warmup   (real synthesis)
          - ASR warmup         (real transcription, Modal or local)

        Memory backend is injected into think once both are ready.
        Modal/ASR warmups are joined before returning so the first user
        message hits warm containers.

        Args:
            on_loading: Called with a progress key when a subsystem starts.
            on_done:    Called with a progress key when a subsystem finishes.
            on_skip:    Called with a progress key when a subsystem is skipped.

        Returns:
            BootResult with think and memorize references; speak and
            listen are always None in this deployment (see module docstring).
        """
        from core.memorize import AikoMemorize
        from core.think    import AikoThink

        memorize  = [None]
        think_ref = [None]
        mem_ready = threading.Event()

        # ── think ─────────────────────────────────────────────────────────────
        def init_think():
            on_loading("think_start")
            think_ref[0] = AikoThink(None, speak=None)
            on_done("think_start")
            on_loading("think_warmup")
            # AikoThink fires its own internal warmup on __init__; join it here
            # Note: we do NOT fire a second Modal LLM warmup from think —
            # _warmup_llm() below handles that with the full soul.md system prompt.
            think_ref[0].join_warmup()
            on_done("think_warmup")
            mem_ready.wait()                        # hold until memorize is ready
            think_ref[0]._memorize = memorize[0]   # inject memory backend

        # ── memorize ──────────────────────────────────────────────────────────
        def init_memorize():
            try:
                on_loading("mem_sqlite_vec")
                memorize[0] = AikoMemorize(silent=True)
                on_done("mem_sqlite_vec")
                on_loading("mem_embed")
                on_done("mem_embed")
                on_loading("mem_cleanup")
                memorize[0].cleanup()
                on_done("mem_cleanup")
                on_loading("mem_ready")
                on_done("mem_ready")
            except Exception as e:
                log.error("Memory boot failed: %s", e)
            finally:
                mem_ready.set()  # always unblock init_think, even on failure

        # ── launch all five concurrently ────────────────────────────────────────
        t_think    = threading.Thread(target=init_think,    daemon=True, name="boot-think")
        t_memorize = threading.Thread(target=init_memorize, daemon=True, name="boot-memorize")
        t_llm      = threading.Thread(
            target=_warmup_llm, args=(on_loading, on_done, on_skip),
            daemon=True, name="warmup-llm"
        )
        t_tts      = threading.Thread(
            target=_warmup_tts, args=(on_loading, on_done, on_skip),
            daemon=True, name="warmup-tts"
        )
        t_asr      = threading.Thread(
            target=_warmup_asr, args=(on_loading, on_done, on_skip),
            daemon=True, name="warmup-asr"
        )

        t_think.start()
        t_memorize.start()
        t_llm.start()
        t_tts.start()
        t_asr.start()

        # Wait for all to complete before returning
        t_think.join()
        t_memorize.join()
        t_llm.join()
        t_tts.join()
        t_asr.join()

        on_skip("speak_skip")
        on_skip("listen_skip")

        return BootResult(
            think    = think_ref[0],
            memorize = memorize[0],
        )