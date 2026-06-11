from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
import gradio as gr
import time
import inspect
import threading
import re

load_dotenv()

print("GRADIO VERSION:", gr.__version__)
print(inspect.signature(gr.Chatbot))

from core.wakeup import AikoWakeup
from ui.css import AIKO_CSS
from ui.asr import transcribe_file
from ui.speak import speak_to_file
from ui.vrm import avatar_html, gradio_file_urls, resolve_vrm_path


# ─────────────────────────────────────────────
# Boot system
# ─────────────────────────────────────────────
result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done=lambda k: print(f"[boot] done: {k}"),
    on_skip=lambda k: print(f"[boot] skip: {k}"),
)

think = result.think
memorize = result.memorize

if hasattr(think, "join_warmup"):
    think.join_warmup()


VRM_PATH = resolve_vrm_path()
VRM_URLS = gradio_file_urls(VRM_PATH)

try:
    gr.set_static_paths(paths=[VRM_PATH.parent])
except Exception:
    pass


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────
def _strip_for_speech(text: str) -> str:
    cleaned = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


_SENTENCE_END = re.compile(r'(?<=[.!?。！？\n])\s*')


def _split_ready_sentences(buffer: str):
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    *complete, remainder = parts
    return [p for p in complete if p.strip()], remainder


# ─────────────────────────────────────────────
# Streaming core
# ─────────────────────────────────────────────
def _stream_response(message: str, history: list):
    history = list(history) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]

    yield history, "", None

    buffer = ""
    full_text = ""

    def _cb(token):
        nonlocal buffer, full_text
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1]
            note = f"\n🔍 Searching: *{query}*\n"
            buffer += note
            full_text += note
        else:
            buffer += token
            full_text += token

    done = threading.Event()
    error = {}

    def _run():
        try:
            think.chat(message, token_callback=_cb)
        except Exception as e:
            error["e"] = e
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()

    while not done.is_set() or buffer.strip():
        sentences, buffer = _split_ready_sentences(buffer)

        for sentence in sentences:
            clean = _strip_for_speech(sentence)
            if not clean:
                continue

            history[-1]["content"] = full_text + ("▋" if not done.is_set() else "")
            audio, emotion = speak_to_file(clean)

            yield history, f"EMOTION:{emotion}|{clean}", audio

        if not sentences:
            history[-1]["content"] = full_text + "▋"
            yield history, "", None
            time.sleep(0.05)

    if buffer.strip():
        clean = _strip_for_speech(buffer)
        history[-1]["content"] = full_text

        if clean:
            audio, emotion = speak_to_file(clean)
            yield history, f"EMOTION:{emotion}|{clean}", audio

    if error:
        raise error["e"]

    history[-1]["content"] = full_text
    yield history, "", None


def text_chat(message: str, history: list):
    history = history or []
    message = (message or "").strip()

    if not message:
        yield history, None, None
        return

    yield from _stream_response(message, history)


def voice_chat(audio_path, history):
    history = history or []

    if not audio_path:
        yield history, None, None
        return

    transcript = transcribe_file(audio_path)

    if not transcript:
        yield history, None, None
        return

    for h, tts, audio in _stream_response(transcript, history):
        if h and len(h) >= 2:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts, audio


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(title="Aiko-chan 🌸", fill_height=True) as demo:

    gr.HTML("""
    <div id="aiko-title">🌸 Aiko-chan</div>
    """)

    with gr.Row(equal_height=True):

        with gr.Column(scale=1, elem_id="aiko-avatar-card"):

            gr.HTML(value=avatar_html(VRM_URLS))

            audio_out = gr.Audio(
                autoplay=True,
                visible=True,
                type="filepath",
                elem_id="aiko-audio",
            )

            tts_text = gr.Textbox(
                value="",
                visible=False,
                elem_id="aiko-tts-text",
            )

            chatbot = gr.Chatbot(
                elem_id="aiko-chatbot",
                height=600,
            )

            with gr.Row(elem_id="aiko-input-row"):
                mic_btn = gr.Button("🎙️", elem_id="aiko-mic-btn")
                msg = gr.Textbox(
                    placeholder="Type a message…",
                    elem_id="aiko-msg",
                    scale=12,
                )
                send = gr.Button("➤", variant="primary")

            mic_audio = gr.Audio(
                sources=["microphone"],
                type="filepath",
                visible=False,
                elem_id="aiko-mic-audio",
            )


# ─────────────────────────────────────────────
# FIXED SUBMIT (THIS WAS YOUR BUG)
# ─────────────────────────────────────────────
def _submit(message, history):
    print("SUBMIT:", repr(message))

    history = history or []

    try:
        for h, tts, audio in text_chat(message, history):
            yield gr.update(value=""), h, tts, audio

    except Exception as e:
        import traceback
        traceback.print_exc()

        history = history + [
            {"role": "assistant", "content": f"ERROR: {e}"}
        ]

        yield gr.update(value=""), history, "", None


# ─────────────────────────────────────────────
# ✅ IMPORTANT: EVENT BINDING (MUST BE OUTSIDE)
# ─────────────────────────────────────────────
msg.submit(
    _submit,
    inputs=[msg, chatbot],
    outputs=[msg, chatbot, tts_text, audio_out],
)

send.click(
    _submit,
    inputs=[msg, chatbot],
    outputs=[msg, chatbot, tts_text, audio_out],
)

mic_audio.change(
    voice_chat,
    inputs=[mic_audio, chatbot],
    outputs=[chatbot, tts_text, audio_out],
)


# ─────────────────────────────────────────────
# Launch
# ─────────────────────────────────────────────
allowed_paths = [
    str(Path("/tmp/aiko_tts")),
    str(VRM_PATH.parent),
]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)