"""
ui/speech.py

Aiko TTS via edge-tts (Microsoft Neural voices, no API key needed).
Returns (sample_rate, np.ndarray) for gr.Audio autoplay.

Voice options (Japanese-accented English or Japanese):
    en-US-AnaNeural, en-US-JennyNeural
    ja-JP-NanamiNeural, ja-JP-MayuNeural
"""

import asyncio
import io
import os
import numpy as np
import soundfile as sf
import edge_tts

EDGE_VOICE = os.getenv("EDGE_VOICE", "en-US-AnaNeural")


async def _synthesize(text: str) -> bytes:
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text, voice=EDGE_VOICE)
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


def speak_to_array(text: str) -> tuple[int, np.ndarray] | None:
    """Synthesize text and return (sample_rate, audio_array) for gr.Audio."""
    if not text or not text.strip():
        return None
    try:
        raw = asyncio.run(_synthesize(text))
        if not raw:
            return None
        audio, sr = sf.read(io.BytesIO(raw))
        return sr, audio.astype(np.float32)
    except Exception as e:
        print(f"[speech] edge-tts error: {e}")
        return None