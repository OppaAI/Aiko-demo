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

# ── Emoji → VRM expression name ───────────────────────────────────────────────
# Keys are single emoji chars; value is the expression name sent to the VRM iframe.
# Falls back to "neutral" when no match.
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
    # blushing / embarrassed  → map to the closest VRM blend shape
    "😳": "surprised", "🥵": "surprised",
    # fun / playful
    "😜": "happy", "😛": "happy", "🤪": "happy", "😝": "happy",
}

def _extract_emotion(text: str) -> str:
    """Return the VRM expression name for the first recognisable emoji in *text*.

    Scans left-to-right; returns 'neutral' when nothing matches.
    """
    for ch in text:
        if ch in _EMOJI_EMOTION:
            return _EMOJI_EMOTION[ch]
    return "neutral"


# ── Text cleaning ─────────────────────────────────────────────────────────────

# Matches a single emoji codepoint (broad range covering most unicode emoji)
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF"   # Misc symbols, pictographs, transport, etc.
    "\U00002600-\U000027BF"    # Misc symbols, dingbats
    "\U0001F000-\U0001F02F"    # Mahjong / domino
    "\U0001F0A0-\U0001F0FF"    # Playing cards
    "\U0001F100-\U0001F1FF"    # Enclosed alphanum supplement
    "\U0001F200-\U0001F2FF"    # Enclosed ideographic supplement
    "\U0001F900-\U0001F9FF"    # Supplemental symbols and pictographs
    "\U0000FE00-\U0000FE0F"    # Variation selectors
    "\U00002000-\U00002BFF"    # General punctuation / arrows / misc technical
    "]+",
    flags=re.UNICODE,
)

# Matches *action text* wrapped in single asterisks, e.g. *smiles quietly*
_ACTION_RE = re.compile(r"\*[^*]+\*")


def _clean_for_tts(text: str) -> str:
    """Strip tokens that make TTS sound awkward: emoji, *actions*, markdown."""
    text = re.sub(r"__SEARCHING__:[^\n]+", "", text)
    text = re.sub(r"\[(?:think|search)[^\]]*\]", "", text, flags=re.I)
    text = _ACTION_RE.sub("", text)       # strip *emote actions*
    text = _EMOJI_RE.sub("", text)        # strip emoji
    text = re.sub(r"[`_#>~]", "", text)   # strip remaining markdown (keep * gone already)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ── TTS synthesis ─────────────────────────────────────────────────────────────

async def _edge_tts_to_file(text: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(
        text,
        voice=EDGE_TTS_VOICE,
        rate=EDGE_TTS_RATE,
        pitch=EDGE_TTS_PITCH,
    )
    await communicate.save(str(out_path))


def speak_to_file(text: str) -> tuple[str | None, str]:
    """Synthesize *text* to an MP3 and return *(filepath, emotion)*.

    - *filepath* is the MP3 path for gr.Audio, or None when text is empty.
    - *emotion* is a VRM expression name string (e.g. 'happy', 'sad', 'neutral').

    Emoji and *action* tokens are stripped from the audio but the emotion they
    carry is captured first and returned so the caller can drive the avatar.
    """
    emotion = _extract_emotion(text)        # read emotion before stripping
    clean = _clean_for_tts(text)

    if not clean:
        return None, emotion

    TTS_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{time.time_ns()}:{clean}".encode("utf-8")).hexdigest()[:16]
    out_path = TTS_DIR / f"aiko_{digest}.mp3"
    asyncio.run(_edge_tts_to_file(clean[:4000], out_path))
    return str(out_path), emotion