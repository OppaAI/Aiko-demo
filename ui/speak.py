"""Browser-friendly TTS helper for the Gradio Space.
The local terminal app plays MioTTS WAV bytes through sounddevice.  In a Space the
browser must do playback, so this helper writes an MP3 file that Gradio's Audio
component can return to the client.
"""
from __future__ import annotations
import hashlib
import asyncio
import os
import queue
import re
import threading
import time
from pathlib import Path

TTS_DIR = Path(os.getenv("AIKO_TTS_DIR", "/tmp/aiko_tts"))
EDGE_TTS_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AvaMultilingualNeural")
EDGE_TTS_RATE = os.getenv("EDGE_TTS_RATE", "+0%")
EDGE_TTS_PITCH = os.getenv("EDGE_TTS_PITCH", "+0Hz")

# URL of your deployed Modal MioTTS endpoint.
# Set MIOTTS_URL in your environment / Gradio Space secrets to enable MioTTS.
# Leave it unset (or empty) to fall back to edge-tts.
# Example: https://oppa-ai-org--miotts-ttsserver-serve.modal.run
MIOTTS_URL = os.getenv("MIOTTS_URL", "").rstrip("/")

# Preset ID registered in MioTTS via register_preset_cli.
# e.g. "Aiko" or "jp_female"
MIOTTS_PRESET_ID = os.getenv("MIOTTS_PRESET_ID", "jp_female")

# ── Emoji → VRM expression name ───────────────────────────────────────────────
_EMOJI_EMOTION: dict[str, str] = {
    "😊": "happy", "😄": "happy", "😁": "happy", "🙂": "happy",
    "😆": "happy", "😂": "happy", "🤣": "happy", "😍": "happy",
    "🥰": "happy", "😇": "happy", "🤩": "happy", "😸": "happy",
    "✨": "happy", "💫": "happy", "🌸": "happy", "💕": "happy",
    "😢": "sad", "😭": "sad", "😔": "sad", "😞": "sad",
    "😟": "sad", "🥺": "sad", "😿": "sad", "💔": "sad",
    "😠": "angry", "😡": "angry", "🤬": "angry", "😤": "angry",
    "👿": "angry", "😾": "angry",
    "😲": "surprised", "😮": "surprised", "🤯": "surprised",
    "😱": "surprised", "😯": "surprised",
    "🤢": "disgusted", "🤮": "disgusted", "😒": "disgusted",
    "🙄": "disgusted", "😑": "disgusted",
    "😌": "relaxed", "🥱": "relaxed", "😴": "relaxed",
    "😳": "surprised", "🥵": "surprised",
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
_SENTENCE_END_RE = re.compile(r'(?<=[.!?…])\s+|(?<=[.!?…])$')


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


def _sentences_from_stream(token_iter):
    """Yield complete sentences as LLM tokens arrive."""
    buf = ""
    for token in token_iter:
        buf += token
        parts = _SENTENCE_END_RE.split(buf)
        for sentence in parts[:-1]:
            sentence = sentence.strip()
            if sentence:
                yield sentence
        buf = parts[-1]
    buf = buf.strip()
    if buf:
        yield buf


# ── TTS backends ──────────────────────────────────────────────────────────────

async def _edge_tts_to_file(text: str, out_path: Path) -> None:
    import edge_tts
    communicate = edge_tts.Communicate(
        text, voice=EDGE_TTS_VOICE, rate=EDGE_TTS_RATE, pitch=EDGE_TTS_PITCH,
    )
    await communicate.save(str(out_path))


def _miotts_to_file(text: str, out_path: Path) -> None:
    """Call MioTTS /v1/tts/file (multipart/form-data) → write WAV then convert to MP3."""
    import httpx
    from pydub import AudioSegment
    import io

    # /v1/tts/file accepts multipart form fields:
    #   text                — required
    #   reference_preset_id — preset name registered via register_preset_cli
    #   output_format       — "wav" returns raw audio/wav bytes directly
    data = {
        "text": text,
        "reference_preset_id": MIOTTS_PRESET_ID,
        "output_format": "wav",
    }

    resp = httpx.post(
        f"{MIOTTS_URL}/v1/tts/file",
        data=data,
        timeout=120,
    )
    resp.raise_for_status()

    # Response is raw WAV bytes (audio/wav) — convert to MP3 for Gradio browser playback
    wav_bytes = io.BytesIO(resp.content)
    audio = AudioSegment.from_wav(wav_bytes)
    audio.export(str(out_path), format="mp3")


def _synth_to_file(clean: str) -> str | None:
    """Synthesize cleaned text, return MP3 path or None on failure."""
    TTS_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(f"{time.time_ns()}:{clean}".encode()).hexdigest()[:16]
    out_path = TTS_DIR / f"aiko_{digest}.mp3"
    try:
        if MIOTTS_URL:
            _miotts_to_file(clean[:4000], out_path)
        else:
            # Fallback: edge-tts (English only, strips non-ASCII)
            clean_ascii = re.sub(r'[^\x00-\x7F]+', ' ', clean).strip()
            if not clean_ascii:
                return None
            asyncio.run(_edge_tts_to_file(clean_ascii[:4000], out_path))
        return str(out_path)
    except Exception as e:
        print(f"[speak] synthesis error: {e}")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def speak_to_file(text: str) -> tuple[str | None, str]:
    """Synthesize *text* to an MP3. Returns (filepath, emotion)."""
    emotion = _extract_emotion(text)
    clean = _clean_for_tts(text)
    if not clean:
        return None, emotion
    path = _synth_to_file(clean)
    return path, emotion


# _SENTINEL signals the ordering queue that a slot is done with no audio
_SENTINEL = object()


def speak_stream(token_iter):
    """Generator: synthesize an LLM token stream sentence-by-sentence.

    Yields (caption: str, audio_path: str | None, emotion: str) tuples
    progressively as each sentence is synthesized, so Gradio can update
    the caption textbox and audio player in real time.

    Each sentence is synthesized in a background thread so LLM parsing and
    synthesis overlap. Yields are emitted in sentence order.

    Usage in Gradio
    ---------------
        def chat(message, history):
            caption_so_far = ""
            for caption, audio_path, emotion in speak_stream(llm.stream(message)):
                caption_so_far += caption + " "
                yield (
                    gr.update(value=caption_so_far),   # Textbox
                    gr.update(value=audio_path),        # Audio  (autoplay=True)
                    emotion,                            # anything else you need
                )

        with gr.Blocks() as demo:
            caption_box = gr.Textbox(label="Caption")
            audio_out   = gr.Audio(autoplay=True, streaming=True)
            msg = gr.Textbox()
            msg.submit(
                chat, [msg], [caption_box, audio_out],
            )
    """
    # Each sentence gets a result_queue slot (in order) that its thread fills.
    # The main thread drains slots in order, so yields are always sequential.
    slots: list[queue.Queue] = []

    def _worker(sentence: str, slot: queue.Queue) -> None:
        emotion = _extract_emotion(sentence)
        clean = _clean_for_tts(sentence)
        if not clean:
            slot.put((sentence, None, emotion))
            return
        path = _synth_to_file(clean)
        slot.put((sentence, path, emotion))

    # Parse sentences and fire a thread per sentence
    for sentence in _sentences_from_stream(token_iter):
        slot: queue.Queue = queue.Queue(maxsize=1)
        slots.append(slot)
        t = threading.Thread(target=_worker, args=(sentence, slot), daemon=True)
        t.start()

    # Drain slots in order — each .get() blocks until that sentence is ready
    for slot in slots:
        sentence, path, emotion = slot.get()
        yield sentence, path, emotion