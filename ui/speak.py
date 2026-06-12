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
import unicodedata
from pathlib import Path

TTS_DIR = Path(os.getenv("AIKO_TTS_DIR", "/tmp/aiko_tts"))
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AvaMultilingualNeural")
EDGE_TTS_RATE = os.getenv("EDGE_TTS_RATE", "+0%")
EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "+0Hz")

# URL of your deployed Modal MioTTS endpoint.
# Set MIOTTS_URL in your environment / Gradio Space secrets to enable MioTTS.
# Leave it unset (or empty) to fall back to edge-tts.
MIOTTS_URL = os.getenv("MIOTTS_URL", "").rstrip("/")

# Optional: preset_id registered in run_server.py via /presets
MIOTTS_PRESET_ID = os.getenv("MIOTTS_PRESET_ID", "")

# ── Emoji → VRM expression name ───────────────────────────────────────────────
_EMOJI_EMOTION: dict[str, str] = {
    # happy / positive
    "😊": "happy", "😄": "happy", "😁": "happy", "🙂": "happy",
    "😆": "happy", "😂": "happy", "🤣": "happy", "😍": "happy",
    "🥰": "happy", "😇": "happy", "🤩": "happy", "😸": "happy",
    "✨": "happy", "💫": "happy", "🌸": "happy", "💕": "happy",
    # sad / melancholy
    "😢": "sad", "😭": "sad", "😔": "sad", "😞": "sad",
    "😟": "sad", "🥺": "sad", "😿": "sad", "💔": "sad",
    # angry / annoyed
    "😠": "angry", "😡": "angry", "🤬": "angry", "😤": "angry",
    "👿": "angry", "😾": "angry",
    # surprised / shocked
    "😲": "surprised", "😮": "surprised", "🤯": "surprised",
    "😱": "surprised", "😯": "surprised",
    # disgusted / skeptical
    "🤢": "disgusted", "🤮": "disgusted", "😒": "disgusted",
    "🙄": "disgusted", "😑": "disgusted",
    # relaxed / neutral-positive
    "😌": "relaxed", "🥱": "relaxed", "😴": "relaxed",
    # blushing / embarrassed
    "😳": "surprised", "🥵": "surprised",
    # fun / playful
    "😜": "happy", "😛": "happy", "🤪": "happy", "😝": "happy",
}


def _is_emoji(ch: str) -> bool:
    cp = ord(ch)
    if cp in (0x200D, 0xFE0E, 0xFE0F):
        return True
    if 0xFE00 <= cp <= 0xFE0F:
        return True
    if 0x1F1E0 <= cp <= 0x1F1FF:
        return True
    emoji_ranges = [
        (0x1F300, 0x1F5FF), (0x1F600, 0x1F64F), (0x1F650, 0x1F67F),
        (0x1F680, 0x1F6FF), (0x1F700, 0x1F77F), (0x1F780, 0x1F7FF),
        (0x1F800, 0x1F8FF), (0x1F900, 0x1F9FF), (0x1FA00, 0x1FA6F),
        (0x1FA70, 0x1FAFF), (0x2600,  0x26FF),  (0x2700,  0x27BF),
        (0x2300,  0x23FF),  (0x25A0,  0x25FF),  (0x2B00,  0x2BFF),
        (0x1F000, 0x1F02F), (0x1F0A0, 0x1F0FF),
    ]
    return any(lo <= cp <= hi for lo, hi in emoji_ranges)


def _extract_emotion(text: str) -> str:
    for ch in text:
        if ch in _EMOJI_EMOTION:
            return _EMOJI_EMOTION[ch]
    return "neutral"


# ── Text cleaning ─────────────────────────────────────────────────────────────

_ACTION_RE = re.compile(r"\*[^*\n]+\*")
_MOOD_PREFIX_RE = re.compile(r"^\s*\S+\s*:\s*")


def _clean_for_tts(text: str) -> str:
    stripped = text.lstrip()
    if stripped and _is_emoji(stripped[0]):
        text = _MOOD_PREFIX_RE.sub("", text, count=1)
    text = re.sub(r"__SEARCHING__:[^\n]+", "", text)
    text = re.sub(r"\[(?:think|search)[^\]]*\]", "", text, flags=re.I)
    text = _ACTION_RE.sub("", text)
    text = re.sub(r"[`_#>~]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── TTS backends ──────────────────────────────────────────────────────────────

async def _edge_tts_to_file(text: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(
        text,
        voice=EDGE_TTS_VOICE,
        rate=EDGE_TTS_RATE,
        pitch=EDGE_TTS_PITCH,
    )
    await communicate.save(str(out_path))


def _miotts_to_file(text: str, out_path: Path) -> None:
    """POST to the Modal MioTTS endpoint and save the returned WAV as MP3."""
    import httpx
    from pydub import AudioSegment
    import io

    payload: dict = {"text": text}
    if MIOTTS_PRESET_ID:
        payload["preset_id"] = MIOTTS_PRESET_ID

    resp = httpx.post(
        f"{MIOTTS_URL}/synthesize",
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()

    # MioTTS returns WAV bytes — convert to MP3 for Gradio
    wav_bytes = io.BytesIO(resp.content)
    audio = AudioSegment.from_wav(wav_bytes)
    audio.export(str(out_path), format="mp3")


# ── Public API ────────────────────────────────────────────────────────────────

def speak_to_file(text: str) -> tuple[str | None, str]:
    """Synthesize *text* to an MP3 and return *(filepath, emotion)*.
    - Uses MioTTS (Modal) when MIOTTS_URL is set, otherwise falls back to edge-tts.
    - *filepath* is the MP3 path for gr.Audio, or None when text is empty.
    - *emotion* is a VRM expression name (e.g. 'happy', 'sad', 'neutral').
    """
    emotion = _extract_emotion(text)
    clean = _clean_for_tts(text)

    if not clean:
        return None, emotion

    # MioTTS handles Unicode fine; edge-tts needs ASCII-only
    if not MIOTTS_URL:
        clean = re.sub(r'[^\x00-\x7F]+', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        if not clean:
            return None, emotion

    TTS_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{time.time_ns()}:{clean}".encode("utf-8")).hexdigest()[:16]
    out_path = TTS_DIR / f"aiko_{digest}.mp3"

    if MIOTTS_URL:
        _miotts_to_file(clean[:4000], out_path)
    else:
        asyncio.run(_edge_tts_to_file(clean[:4000], out_path))

    return str(out_path), emotion


# ── Streaming / close-caption TTS ────────────────────────────────────────────

import threading
import queue

# Sentence-ending punctuation that triggers a TTS flush
_SENTENCE_END_RE = re.compile(r'(?<=[.!?…])\s+|(?<=[.!?…])$')


def _sentences_from_stream(token_iter):
    """Yield complete sentences as an LLM token stream arrives.
    Buffers tokens and flushes on sentence-ending punctuation.
    """
    buf = ""
    for token in token_iter:
        buf += token
        parts = _SENTENCE_END_RE.split(buf)
        # All but the last part are complete sentences
        for sentence in parts[:-1]:
            sentence = sentence.strip()
            if sentence:
                yield sentence
        buf = parts[-1]
    # Flush whatever's left
    buf = buf.strip()
    if buf:
        yield buf


def speak_stream(
    token_iter,
    on_audio: callable,
    on_caption: callable | None = None,
) -> None:
    """Feed an LLM token iterator into MioTTS sentence-by-sentence.

    Parameters
    ----------
    token_iter   : iterable of str tokens from your LLM stream
    on_audio     : callback(mp3_path: str) called for each synthesized sentence
                   — pass to gr.Audio or queue for playback
    on_caption   : optional callback(sentence: str) called with the text
                   just before synthesis starts — use for close-caption display

    The synthesis of sentence N overlaps with the LLM generating sentence N+1,
    so perceived latency is roughly one sentence's worth of LLM tokens.

    Example (Gradio):
        captions = []
        audio_queue = []

        def handle_audio(path):
            audio_queue.append(path)

        def handle_caption(text):
            captions.append(text)
            # yield to gr.Textbox update here

        speak_stream(llm.stream("Tell me a story"), handle_audio, handle_caption)
    """
    if not MIOTTS_URL:
        raise RuntimeError(
            "MIOTTS_URL is not set. speak_stream requires the Modal MioTTS endpoint."
        )

    audio_q: queue.Queue[str | None] = queue.Queue()

    def _synth_worker(sentence: str) -> None:
        emotion = _extract_emotion(sentence)
        clean = _clean_for_tts(sentence)
        if not clean:
            return
        TTS_DIR.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(f"{time.time_ns()}:{clean}".encode()).hexdigest()[:16]
        out_path = TTS_DIR / f"aiko_{digest}.mp3"
        try:
            _miotts_to_file(clean[:4000], out_path)
            audio_q.put(str(out_path))
        except Exception as e:
            print(f"[speak_stream] synthesis error: {e}")

    active_threads: list[threading.Thread] = []

    for sentence in _sentences_from_stream(token_iter):
        if on_caption:
            on_caption(sentence)

        # Fire synthesis in a background thread so LLM parsing continues
        t = threading.Thread(target=_synth_worker, args=(sentence,), daemon=True)
        t.start()
        active_threads.append(t)

    # Wait for all synthesis threads, drain audio in order
    for t in active_threads:
        t.join()

    # Drain the queue and call on_audio in arrival order
    # (threads finish roughly in order; queue reflects synthesis completion order)
    while not audio_q.empty():
        path = audio_q.get_nowait()
        on_audio(path)