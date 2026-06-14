"""Browser-upload ASR helper for the Gradio Space.

The terminal listener captures local PulseAudio. In Gradio/HF Spaces the browser
records the microphone and uploads a file, so this module transcribes that uploaded
file by posting it to the Modal Nemotron ASR endpoint.
Falls back to local faster-whisper when AIKO_ASR_URL is not set.

Env vars:
    AIKO_ASR_URL      Full Modal endpoint URL, e.g.
                      https://oppa-ai-org--aiko-nemotron-asr-transcribe.modal.run
    AIKO_ASR_LANG     BCP-47 language tag (e.g. "ja-JP", "en-US").
                      Omit or set to "auto" for Nemotron auto language-ID.

Local fallback env vars (only used when AIKO_ASR_URL is not set):
    AIKO_ASR_MODEL    faster-whisper model size (default: "base")
    AIKO_ASR_DEVICE   "auto" | "cuda" | "cpu"  (default: "auto")
    AIKO_ASR_COMPUTE  compute type hint         (default: "default")
    AIKO_ASR_BEAM_SIZE beam size                (default: 5)
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Modal ASR endpoint — set this in your Gradio Space secrets
# ---------------------------------------------------------------------------
ASR_URL = os.getenv("AIKO_ASR_URL", "").rstrip("/")

# Language hint for Nemotron (omit for auto langid across 40 locales)
ASR_LANG = os.getenv("AIKO_ASR_LANG", "").strip() or None

# ---------------------------------------------------------------------------
# Local fallback config (used when AIKO_ASR_URL is not set)
# ---------------------------------------------------------------------------
_MODEL: Any | None = None
_MODEL_LOCK = threading.Lock()


def _resolve_device(device_hint: str, compute_hint: str) -> tuple[str, str]:
    if device_hint != "auto":
        return device_hint, compute_hint
    import torch
    if torch.cuda.is_available():
        return "cuda", "float16" if compute_hint == "default" else compute_hint
    return "cpu", "int8" if compute_hint in {"default", "float16"} else compute_hint


def _local_model():
    global _MODEL
    with _MODEL_LOCK:
        if _MODEL is None:
            from faster_whisper import WhisperModel
            model_size = os.getenv("AIKO_ASR_MODEL", os.getenv("WHISPER_MODEL", "base"))
            device_hint = os.getenv("AIKO_ASR_DEVICE", os.getenv("WHISPER_DEVICE", "auto"))
            compute_hint = os.getenv("AIKO_ASR_COMPUTE", os.getenv("WHISPER_COMPUTE", "default"))
            device, compute = _resolve_device(device_hint, compute_hint)
            _MODEL = WhisperModel(model_size, device=device, compute_type=compute)
    return _MODEL


# ---------------------------------------------------------------------------
# Transcription backends
# ---------------------------------------------------------------------------

def _transcribe_modal(audio_path: str) -> str:
    """POST audio file to the Modal Nemotron ASR endpoint.

    The endpoint is the full URL (no sub-path needed):
        POST <ASR_URL>
        multipart/form-data fields:
            audio    — wav file
            language — BCP-47 tag or omitted for auto langid
    """
    import httpx

    fields: dict = {}
    if ASR_LANG and ASR_LANG.lower() != "auto":
        fields["language"] = ASR_LANG

    with open(audio_path, "rb") as f:
        resp = httpx.post(
            ASR_URL,                             # endpoint IS the full URL
            files={"audio": (Path(audio_path).name, f, "audio/wav")},
            data=fields,
            timeout=60,                          # Nemotron cold-start can be slow
        )

    resp.raise_for_status()
    return resp.json().get("text", "").strip()


def _transcribe_local(audio_path: str) -> str:
    """Transcribe using local faster-whisper (fallback)."""
    language = os.getenv("AIKO_ASR_LANG", os.getenv("WHISPER_LANG", "")) or None
    segments, _ = _local_model().transcribe(
        audio_path,
        language=language,
        beam_size=int(os.getenv("AIKO_ASR_BEAM_SIZE", "5")),
        vad_filter=True,
        condition_on_previous_text=False,
    )
    return " ".join(s.text.strip() for s in segments).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def transcribe_file(audio_path: str | Path | None) -> str:
    """Transcribe a browser-recorded microphone file.

    Uses the Modal Nemotron ASR endpoint when AIKO_ASR_URL is set,
    otherwise falls back to local faster-whisper.

    Args:
        audio_path: Path to the audio file recorded by the Gradio mic component.

    Returns:
        Transcribed text, or empty string if audio_path is None/empty.
    """
    if not audio_path:
        return ""

    audio_path = str(audio_path)

    if ASR_URL:
        return _transcribe_modal(audio_path)
    return _transcribe_local(audio_path)