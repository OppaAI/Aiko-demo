"""
ui/speech.py
Aiko TTS via edge-tts — returns a filepath for gr.Audio(type="filepath").
"""
import asyncio
import os
import threading
import uuid

import edge_tts

EDGE_VOICE = os.getenv("EDGE_VOICE", "en-US-AnaNeural")
_AUDIO_DIR  = "/tmp/aiko_tts"
_SYNTH_TIMEOUT = 15


async def _synthesize(text: str, path: str) -> None:
    communicate = edge_tts.Communicate(text, voice=EDGE_VOICE)
    await communicate.save(path)


def speak_to_file(text: str) -> str | None:
    """Synthesize text and return an .mp3 filepath for gr.Audio(type='filepath')."""
    if not text or not text.strip():
        return None

    os.makedirs(_AUDIO_DIR, exist_ok=True)
    output_path = os.path.join(_AUDIO_DIR, f"{uuid.uuid4()}.mp3")

    print(f"[speech] synthesizing {len(text)} chars via {EDGE_VOICE} → {output_path}")

    exc: list[Exception | None] = [None]

    def _run() -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_synthesize(text, output_path))
            loop.close()
        except Exception as e:
            exc[0] = e

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=_SYNTH_TIMEOUT)

    if t.is_alive():
        print(f"[speech] edge-tts timed out after {_SYNTH_TIMEOUT}s")
        return None

    if exc[0]:
        print(f"[speech] edge-tts error: {exc[0]}")
        return None

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        print("[speech] output file missing or empty")
        return None

    return output_path