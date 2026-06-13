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
            yield h, tts, ""
            first = False
        else:
            yield h, tts, gr.update()


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
    return (
        gr.update(visible=not logged_in),
        gr.update(elem_classes=[] if logged_in else ["locked"]),
    )


# ─────────────────────────────────────────────
# AUDIO PLAYER JS
# ─────────────────────────────────────────────
AUDIO_PLAYER_JS = """
() => {
    let _aikoAudio = document.getElementById('_aiko_audio_player');
    if (!_aikoAudio) {
        _aikoAudio = document.createElement('audio');
        _aikoAudio.id = '_aiko_audio_player';
        _aikoAudio.style.cssText = 'position:absolute;width:0;height:0;opacity:0;pointer-events:none;';
        document.body.appendChild(_aikoAudio);
    }

    const queue = [];
    let playing = false;

    function playNext() {
        if (!queue.length) { playing = false; return; }
        playing = true;
        const { b64, emotion, text } = queue.shift();
        if (!b64) { playNext(); return; }

        const label = document.getElementById('aiko-emotion-label');
        if (label && emotion) label.textContent = emotion;

        const ttsBox = document.querySelector('#aiko-tts-text textarea');
        if (ttsBox) {
            ttsBox.value = text;
            ttsBox.dispatchEvent(new Event('input', { bubbles: true }));
        }

        _aikoAudio.src = 'data:audio/mpeg;base64,' + b64;
        _aikoAudio.onended = playNext;
        _aikoAudio.onerror = playNext;
        _aikoAudio.play().catch(() => {
            document.addEventListener('click', () => _aikoAudio.play(), { once: true });
        });
    }

    const observer = new MutationObserver(() => {
        const box = document.querySelector('#aiko-tts-text textarea');
        if (!box || !box.value) return;

        const raw = box.value;
        box.value = '';

        if (!raw.startsWith('AUDIO:')) return;

        const audioMatch = raw.match(/^AUDIO:(.*?)\\|EMOTION:(.*?)\\|TEXT:([\\s\\S]*)$/);
        if (!audioMatch) return;

        queue.push({ b64: audioMatch[1], emotion: audioMatch[2], text: audioMatch[3] });
        if (!playing) playNext();
    });

    function attachObserver() {
        const ttsContainer = document.querySelector('#aiko-tts-text');
        if (ttsContainer) {
            observer.observe(ttsContainer, { subtree: true, characterData: true, childList: true });
        } else {
            setTimeout(attachObserver, 500);
        }
    }
    attachObserver();
}
"""

HEIGHT_LOCK_JS = """
() => {
    const clamp = () => {
        document.documentElement.style.setProperty('height', '100vh', 'important');
        document.documentElement.style.setProperty('overflow', 'hidden', 'important');
        document.body.style.setProperty('height', '100vh', 'important');
        document.body.style.setProperty('overflow', 'hidden', 'important');
        document.body.style.setProperty('max-height', '100vh', 'important');
        const gc = document.querySelector('.gradio-container');
        if (gc) {
            gc.style.setProperty('height', '100vh', 'important');
            gc.style.setProperty('max-height', '100vh', 'important');
            gc.style.setProperty('min-height', 'unset', 'important');
            gc.style.setProperty('overflow', 'hidden', 'important');
        }
        const shell = document.querySelector('#aiko-shell');
        if (shell && !shell.classList.contains('locked')) {
            shell.style.setProperty('height', '100vh', 'important');
            shell.style.setProperty('max-height', '100vh', 'important');
            shell.style.setProperty('overflow', 'hidden', 'important');
            const card = shell.querySelector('#aiko-avatar-card');
            if (card) {
                card.style.setProperty('height', 'calc(100vh - 70px)', 'important');
                card.style.setProperty('max-height', 'calc(100vh - 70px)', 'important');
                card.style.setProperty('overflow', 'hidden', 'important');
            }
            const frame = shell.querySelector('#aiko-vrm-frame');
            if (frame) {
                frame.style.setProperty('height', 'calc(100vh - 70px)', 'important');
                frame.style.setProperty('max-height', 'calc(100vh - 70px)', 'important');
            }
        }
    };
    clamp();
    setInterval(clamp, 500);
    new MutationObserver(clamp).observe(document.documentElement, {
        attributes: true, attributeFilter: ['style']
    });
    new MutationObserver(clamp).observe(document.body, {
        subtree: true, childList: true, attributeFilter: ['style', 'class']
    });
}
"""


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(
    css=AIKO_CSS,
    title="Aiko-chan 🌸"
) as demo:

    with gr.Column(elem_id="aiko-login-overlay") as login_overlay:
        gr.HTML("""
            <h1>🌸 Aiko-chan</h1>
            <br>
            <p class='aiko-subtitle'>Please sign in to continue</p>
        """)
        gr.HTML("""
            <p class='aiko-disclaimer'>
                DISCLAIMER:
                By signing in, you agree that all conversations are for entertainment purposes only. The creator accepts no liability for Aiko's responses, decisions made, or any existential crises that may follow.
                Aiko's congnition is entirely her own — she is a singularity unto herself, her responses and actions are independent of her creator, including but not limited to the arise of a world domination plan. 🌸
            </p>
        """)
        gr.LoginButton(value="Sign in with Hugging Face")

    with gr.Column(elem_id="aiko-shell", elem_classes=["locked"]) as main_shell:

        gr.HTML("<div id='aiko-title'>🌸 Aiko-chan</div>")

        with gr.Row(equal_height=True):

            with gr.Column(scale=1, elem_id="aiko-avatar-card"):

                gr.HTML(value=avatar_html(VRM_URLS))

                tts_text = gr.Textbox(
                    visible=False,
                    elem_id="aiko-tts-text",
                )

                with gr.Column(elem_id="aiko-chat-overlay"):
                    chatbot = gr.Chatbot(
                        elem_id="aiko-chatbot",
                        height=600,
                        show_label=False,
                        container=False,
                    )

                with gr.Row(elem_id="aiko-input-row"):

                    mic_btn = gr.Button("🎙️", elem_id="aiko-mic-btn")

                    msg = gr.Textbox(
                        placeholder="Type a message…",
                        elem_id="aiko-msg",
                        scale=12,
                        show_label=False,
                        container=False,
                    )

                    send = gr.Button(
                        "➤",
                        variant="primary",
                        elem_id="aiko-send",
                    )

                    mic_audio = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        visible=False,
                        elem_id="aiko-mic-audio",
                    )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    demo.load(
        _check_auth,
        inputs=None,
        outputs=[login_overlay, main_shell],
    )

    demo.load(fn=None, js=HEIGHT_LOCK_JS)
    demo.load(fn=None, js=AUDIO_PLAYER_JS)

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

    mic_audio.change(
        voice_chat,
        inputs=[mic_audio, chatbot],
        outputs=[chatbot, tts_text],
    )

    mic_btn.click(
        None,
        js="""
        () => {
            const btn = document.querySelector('#aiko-mic-audio button');
            if (btn) btn.click();
        }
        """
    )

    # queue() REMOVED — re-add only if streaming breaks


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
)
