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
from ui.vrm import avatar_html, gradio_file_urls, resolve_vrm_path
from ui.listen import transcribe_file
from ui.speak import speak_to_file


# ─────────────────────────────────────────────
# BOOT
# ─────────────────────────────────────────────
result = AikoWakeup().boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done=lambda k: print(f"[boot] done: {k}"),
    on_skip=lambda k: print(f"[boot] skip: {k}"),
)

think = result.think

if hasattr(think, "join_warmup"):
    think.join_warmup()


VRM_PATH = resolve_vrm_path()
VRM_URLS = gradio_file_urls(VRM_PATH)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def _strip_for_speech(text: str) -> str:
    text = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    text = re.sub(r"\n?🔧 .*?\n?", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    return text.strip()


_SENTENCE_END = re.compile(r'(?<=[.!?。！？\n])\s*')


def _split_ready_sentences(buffer: str):
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    *complete, remainder = parts
    return [p for p in complete if p.strip()], remainder


# ─────────────────────────────────────────────
# STREAM CORE
# ─────────────────────────────────────────────
def _stream_response(message: str, history: list, user_id: str = "OppaAI"):
    history = list(history) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]

    yield history, None

    buffer = ""
    full_text = ""
    last_emitted = ""

    done = threading.Event()
    error = {}

    def _cb(token):
        nonlocal buffer, full_text

        if token.startswith("__SEARCHING__:"):
            q = token.split(":", 1)[1]
            note = f"\n🔍 Searching: *{q}*\n"
            buffer += note
            full_text += note
        elif token.startswith("__TOOL__:"):
            note = token.split(":", 1)[1]
            display = f"\n🔧 {note}\n"
            buffer += display
            full_text += display
        else:
            buffer += token
            full_text += token

    def _run():
        try:
            think.chat(message, user_id=user_id, token_callback=_cb)
        except Exception as e:
            error["e"] = e
        finally:
            done.set()

    threading.Thread(target=_run, daemon=True).start()

    while not done.is_set() or full_text != last_emitted:

        if full_text != last_emitted:
            history[-1]["content"] = full_text + ("▋" if not done.is_set() else "")
            last_emitted = full_text
            yield history, None

        sentences, buffer = _split_ready_sentences(buffer)

        for s in sentences:
            clean = _strip_for_speech(s)
            if not clean:
                continue

            audio_path, emotion = speak_to_file(clean)
            audio_b64 = _encode_audio_b64(audio_path)
            payload = f"AUDIO:{audio_b64}|EMOTION:{emotion}|TEXT:{clean}"
            yield history, payload

        time.sleep(0.03)

    if buffer.strip():
        clean = _strip_for_speech(buffer)
        if clean:
            audio_path, emotion = speak_to_file(clean)
            audio_b64 = _encode_audio_b64(audio_path)
            payload = f"AUDIO:{audio_b64}|EMOTION:{emotion}|TEXT:{clean}"
            yield history, payload

    if error:
        raise error["e"]

    history[-1]["content"] = full_text
    yield history, None


def _encode_audio_b64(audio_path: str | None) -> str:
    if not audio_path:
        return ""
    try:
        import base64
        with open(audio_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception:
        return ""


# ─────────────────────────────────────────────
# WRAPPERS
# ─────────────────────────────────────────────
def _submit(message, history, profile: gr.OAuthProfile | None = None):
    history = history or []
    message = (message or "").strip()
    user_id = profile.username if profile else "guest"

    if not message:
        yield history, None, message
        return

    first = True
    for h, tts in _stream_response(message, history, user_id):
        if first:
            yield h, tts or "", ""
            first = False
        else:
            yield h, tts or "", gr.update()


def voice_chat(audio_path, history, profile: gr.OAuthProfile | None = None):
    history = history or []
    user_id = profile.username if profile else "guest"

    if not audio_path:
        return history, None

    transcript = transcribe_file(audio_path)

    if not transcript:
        return history, None

    for h, tts in _stream_response(transcript, history, user_id):
        if h and len(h) >= 2:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts


# ─────────────────────────────────────────────
# AUTH GATE
# ─────────────────────────────────────────────
def _check_auth(profile: gr.OAuthProfile | None = None):
    logged_in = profile is not None
    print(f"[auth] profile={profile!r} logged_in={logged_in}")
    return (
        gr.update(visible=not logged_in),
        gr.update(),
    )


# ─────────────────────────────────────────────
# UI  (MINIMAL DIAGNOSTIC VERSION)
# ─────────────────────────────────────────────
with gr.Blocks(title="Aiko-chan 🌸 [TEST]") as demo:

    # Login overlay — visible by default, hidden after auth
    with gr.Column(elem_id="aiko-login-overlay", visible=True) as login_overlay:
        gr.HTML("""
            <h1>🌸 Aiko-chan [TEST]</h1>
            <br>
            <p class='aiko-subtitle'>Please sign in to continue</p>
        """)
        gr.LoginButton(value="Sign in with Hugging Face")

    # Main shell — ALWAYS visible (login overlay covers it via CSS z-index,
    # but since we're testing with no/partial CSS, this also stays visible
    # so we can confirm whether content renders at all)
    with gr.Column(elem_id="aiko-shell", visible=True) as main_shell:

        gr.Markdown("# HELLO WORLD — if you can see this, basic rendering works")

        tts_text = gr.Textbox(visible=False, elem_id="aiko-tts-text")

        chatbot = gr.Chatbot(
            elem_id="aiko-chatbot",
            height=400,
            show_label=False,
        )

        with gr.Row(elem_id="aiko-input-row"):
            msg = gr.Textbox(
                placeholder="Type a message…",
                elem_id="aiko-msg",
                scale=12,
                show_label=False,
            )
            send = gr.Button(
                "➤",
                variant="primary",
                elem_id="aiko-send",
            )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────

    demo.load(
        _check_auth,
        inputs=None,
        outputs=[login_overlay, main_shell],
    )

    msg.submit(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, msg],
    )

    send.click(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, msg],
    )


# ─────────────────────────────────────────────
# LAUNCH
# ─────────────────────────────────────────────
allowed_paths = [
    str(Path("/tmp/aiko_tts")),
    str(VRM_PATH.parent),
]

demo.queue()
demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
    css=AIKO_CSS,
)