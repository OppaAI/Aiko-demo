"""
ui/speech.py

Kokoro-82M TTS for HF Spaces — returns (sample_rate, np.ndarray) for gr.Audio.
No sounddevice, no server — audio bytes go to the browser via Gradio.

Install:
    pip install kokoro>=0.9.4 soundfile
    apt-get install -y espeak-ng      # required by kokoro's phonemizer

Usage:
    from ui.speech import speak_to_array
    sr, audio = speak_to_array("Hello!")   # plug into gr.Audio output
"""

import os
import numpy as np

# Voice options (English female, sounds closest to a soft JP-EN accent):
#   af_heart, af_bella, af_sarah, af_nicole, af_sky
KOKORO_VOICE  = os.getenv("KOKORO_VOICE", "af_heart")
KOKORO_LANG   = os.getenv("KOKORO_LANG",  "a")   # 'a' = American English
SAMPLE_RATE   = 24000

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from kokoro import KPipeline
        _pipeline = KPipeline(lang_code=KOKORO_LANG)
    return _pipeline


def speak_to_array(text: str) -> tuple[int, np.ndarray] | None:
    """
    Synthesize text with Kokoro and return (sample_rate, audio_array).
    Returns None on failure so the caller can degrade gracefully.
    Concatenates chunks so the full response plays as one clip.
    """
    if not text or not text.strip():
        return None
    try:
        pipeline  = _get_pipeline()
        chunks    = []
        generator = pipeline(text, voice=KOKORO_VOICE)
        for _gs, _ps, audio in generator:
            if audio is not None and len(audio) > 0:
                chunks.append(audio)
        if not chunks:
            return None
        full_audio = np.concatenate(chunks).astype(np.float32)
        return SAMPLE_RATE, full_audio
    except Exception as e:
        print(f"[speech] Kokoro error: {e}")
        return None