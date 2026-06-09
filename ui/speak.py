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
import threading
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
        # Run in a dedicated thread with its own event loop to avoid
        # "This event loop is already running" when called from Gradio's loop.
        print(f"[speech] synthesizing {len(text)} chars via {EDGE_VOICE}")
        result = [None]
        exc    = [None]

        def _run():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result[0] = loop.run_until_complete(_synthesize(text))
                loop.close()
            except Exception as e:
                exc[0] = e

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        t.join()

        if exc[0]:
            raise exc[0]
        raw = result[0]
        if not raw:
            return None
        audio, sr = sf.read(io.BytesIO(raw))
        return sr, audio.astype(np.float32)
    except Exception as e:
        print(f"[speech] edge-tts error: {e}")
        return None