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