"""Browser-friendly TTS helper for the Gradio Space.

The local terminal app plays MioTTS WAV bytes through sounddevice.  In a Space the
browser must do playback, so this helper writes an MP3 file that Gradio's Audio
component can return to the client.
"""

from __future__ import annotations

import asyncio
import hashlib
import os
import re
import time
from pathlib import Path

TTS_DIR = Path(os.getenv("AIKO_TTS_DIR", "/tmp/aiko_tts"))
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AvaMultilingualNeural")
EDGE_TTS_RATE = os.getenv("EDGE_TTS_RATE", "+0%")
EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "+0Hz")


def _clean_text(text: str) -> str:
    """Strip markdown/control tokens that make TTS sound awkward."""
    text = re.sub(r"__SEARCHING__:[^\n]+", "", text)
    text = re.sub(r"\[(?:think|search)[^\]]*\]", "", text, flags=re.I)
    text = re.sub(r"[`*_#>~]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


async def _edge_tts_to_file(text: str, out_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(
        text,
        voice=EDGE_TTS_VOICE,
        rate=EDGE_TTS_RATE,
        pitch=EDGE_TTS_PITCH,
    )
    await communicate.save(str(out_path))


def speak_to_file(text: str) -> str | None:
    """Synthesize *text* to an MP3 and return the filepath for gr.Audio.

    Returns None when the text is empty.  Exceptions are intentionally allowed to
    surface so Space logs show TTS failures clearly.
    """
    text = _clean_text(text)
    if not text:
        return None

    TTS_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{time.time_ns()}:{text}".encode("utf-8")).hexdigest()[:16]
    out_path = TTS_DIR / f"aiko_{digest}.mp3"
    asyncio.run(_edge_tts_to_file(text[:4000], out_path))
    return str(out_path)