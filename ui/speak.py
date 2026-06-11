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
    """Return True if *ch* is an emoji or emoji modifier/variation character.
    Uses unicodedata category + explicit block ranges instead of a broad
    character-class regex so we never accidentally eat punctuation.
    """
    cp = ord(ch)
    # Variation selectors and zero-width joiners that attach to emoji
    if cp in (0x200D, 0xFE0E, 0xFE0F):
        return True
    # Keycap combining chars
    if 0xFE00 <= cp <= 0xFE0F:
        return True
    # Enclosed alphanumerics / regional indicators
    if 0x1F1E0 <= cp <= 0x1F1FF:
        return True
    # Main emoji blocks (carefully bounded — NOT including general punctuation)
    emoji_ranges = [
        (0x1F300, 0x1F5FF),  # Misc symbols & pictographs
        (0x1F600, 0x1F64F),  # Emoticons
        (0x1F650, 0x1F67F),  # Ornamental dingbats
        (0x1F680, 0x1F6FF),  # Transport & map
        (0x1F700, 0x1F77F),  # Alchemical symbols
        (0x1F780, 0x1F7FF),  # Geometric shapes extended
        (0x1F800, 0x1F8FF),  # Supplemental arrows-C
        (0x1F900, 0x1F9FF),  # Supplemental symbols & pictographs
        (0x1FA00, 0x1FA6F),  # Chess symbols
        (0x1FA70, 0x1FAFF),  # Symbols and pictographs extended-A
        (0x2600,  0x26FF),   # Misc symbols (☀ ⛅ etc.)
        (0x2700,  0x27BF),   # Dingbats
        (0x2300,  0x23FF),   # Misc technical (⏰ etc.)
        (0x25A0,  0x25FF),   # Geometric shapes
        (0x2B00,  0x2BFF),   # Misc symbols and arrows (⭐ etc.)
        (0x1F000, 0x1F02F),  # Mahjong tiles
        (0x1F0A0, 0x1F0FF),  # Playing cards
    ]
    return any(lo <= cp <= hi for lo, hi in emoji_ranges)


def _extract_emotion(text: str) -> str:
    """Return the VRM expression name for the first recognisable emoji in *text*.
    Soul.md format is '<emoji>:' at the very start of the response.
    Scans left-to-right; returns 'neutral' when nothing matches.
    """
    for ch in text:
        if ch in _EMOJI_EMOTION:
            return _EMOJI_EMOTION[ch]
    return "neutral"


# ── Text cleaning ─────────────────────────────────────────────────────────────

# Matches *action text* wrapped in single asterisks, e.g. *adjusts imaginary sleeves*
_ACTION_RE = re.compile(r"\*[^*\n]+\*")

# Soul.md prefixes each response with a mood emoji followed by a colon, e.g. "😊: "
# Strip that leading token entirely from TTS — it's visual-only.
_MOOD_PREFIX_RE = re.compile(r"^\s*\S+\s*:\s*")  # catches "😊: " or "😊 :"


def _clean_for_tts(text: str) -> str:
    """Strip tokens that make TTS sound awkward.
    Removes (in order):
      - soul.md mood-emoji prefix  (e.g. "😊: ")
      - __SEARCHING__ status lines
      - [think]/[search] bracketed tokens
      - *asterisk action text*
      - leftover markdown characters
      - excess whitespace
    NOTE: emoji are intentionally NOT stripped from the remaining text —
    edge-tts will read/voice them (or silently skip ones it can't render).
    """
    # Strip soul.md leading mood prefix only if first non-space char is emoji
    stripped = text.lstrip()
    if stripped and _is_emoji(stripped[0]):
        text = _MOOD_PREFIX_RE.sub("", text, count=1)

    text = re.sub(r"__SEARCHING__:[^\n]+", "", text)
    text = re.sub(r"\[(?:think|search)[^\]]*\]", "", text, flags=re.I)
    text = _ACTION_RE.sub("", text)
    text = re.sub(r"[`_#>~]", "", text)   # remaining markdown (asterisks already gone)
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
    - *emotion* is a VRM expression name (e.g. 'happy', 'sad', 'neutral').
    Emotion is captured from the leading mood emoji (which is then stripped
    along with the ':' separator); any other emoji in the body are left in
    place and passed through to TTS.
    """
    emotion = _extract_emotion(text)   # read before stripping the mood prefix
    clean = _clean_for_tts(text)

    if not clean:
        return None, emotion

    TTS_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{time.time_ns()}:{clean}".encode("utf-8")).hexdigest()[:16]
    out_path = TTS_DIR / f"aiko_{digest}.mp3"
    asyncio.run(_edge_tts_to_file(clean[:4000], out_path))
    return str(out_path), emotion