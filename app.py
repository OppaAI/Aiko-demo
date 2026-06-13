from __future__ import annotations

from pathlib import Path
from dotenv import load_dotenv
from datetime import date
import gradio as gr
from gradio import OAuthProfile
import time
import inspect
import threading
import queue
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
# SOUL PROMPT INJECTION
# ─────────────────────────────────────────────
SOUL_TEMPLATE_PATH = Path("persona/soul.md")

def build_soul_prompt(user_id: str) -> str:
    template = SOUL_TEMPLATE_PATH.read_text(encoding="utf-8")
    today = date.today().strftime("%B %d, %Y")
    return (
        template
        .replace("USER_ID_HERE", user_id)
        .replace("TODAY_HERE", today)
    )


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
_DONE = object()  # sentinel


def _stream_response(message: str, history: list):
    """
    Pipeline:
      1. LLM streams tokens in background thread → sentence queue
      2. Per sentence: TTS synthesis fires in background thread → audio queue
      3. Gradio yields text+audio sentence by sentence as TTS completes
      4. Chatbot shows text in sync with audio playback (sentence revealed
         only when its audio is ready), input unlocks after all TTS done.
    """
    history = list(history) + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]
    yield history, None, None

    # ── Stage 1: LLM → sentence queue ────────────────────────────────────────
    sentence_q: queue.Queue = queue.Queue()
    llm_error = {}

    def _llm_thread():
        buffer = ""
        full_text = ""

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

            # Push complete sentences into queue as they arrive
            sentences, new_buf = _split_ready_sentences(buffer)
            buffer = new_buf
            for s in sentences:
                sentence_q.put(("sentence", s, full_text))

        try:
            think.chat(message, token_callback=_cb)
        except Exception as e:
            llm_error["e"] = e
        finally:
            # Flush remaining buffer
            if buffer.strip():
                sentence_q.put(("sentence", buffer.strip(), full_text))
            sentence_q.put(("done", full_text, full_text))

    threading.Thread(target=_llm_thread, daemon=True).start()

    # ── Stage 2: sentence → TTS queue (parallel synthesis) ───────────────────
    # Each sentence slot: (sentence_text, full_text_so_far, audio_queue)
    # Audio synthesis fires immediately when sentence is ready; we drain
    # in order so playback is sequential.
    slots: list[tuple[str, str, queue.Queue]] = []
    llm_done = threading.Event()
    final_text = [""]

    def _tts_worker(sentence: str, full_text: str, slot: queue.Queue):
        clean = _strip_for_speech(sentence)
        if not clean:
            slot.put((None, "neutral", sentence, full_text))
            return
        audio, emotion = speak_to_file(clean)
        slot.put((audio, emotion, sentence, full_text))

    # Collect sentences and fire TTS threads
    def _dispatch_thread():
        while True:
            kind, sentence, full_text = sentence_q.get()
            if kind == "done":
                final_text[0] = full_text
                llm_done.set()
                break
            slot: queue.Queue = queue.Queue(maxsize=1)
            slots.append(slot)
            threading.Thread(
                target=_tts_worker,
                args=(sentence, full_text, slot),
                daemon=True,
            ).start()

    threading.Thread(target=_dispatch_thread, daemon=True).start()

    # ── Stage 3: drain slots in order, yield text+audio together ─────────────
    # Show a "thinking" indicator while waiting for first sentence
    displayed_text = ""
    slot_idx = 0

    while True:
        # Check if new slots have appeared
        if slot_idx < len(slots):
            slot = slots[slot_idx]
            audio, emotion, sentence, full_text_snapshot = slot.get()  # blocks until TTS done

            # Reveal this sentence's text in sync with its audio
            displayed_text += sentence + " "
            history[-1]["content"] = displayed_text.strip()

            yield (
                history,
                f"EMOTION:{emotion}|{_strip_for_speech(sentence)}",
                audio,
            )
            slot_idx += 1

        elif llm_done.is_set() and slot_idx >= len(slots):
            # All sentences dispatched and drained
            break
        else:
            # Still waiting for more sentences or TTS
            time.sleep(0.05)

    # Final cleanup — ensure full text is shown (covers edge case of no sentences)
    if final_text[0] and history[-1]["content"] != final_text[0]:
        history[-1]["content"] = final_text[0]

    yield history, None, None

    if llm_error:
        raise llm_error["e"]


# ─────────────────────────────────────────────
# WRAPPERS
# ─────────────────────────────────────────────
def _submit(message, history):
    history = history or []
    message = (message or "").strip()

    if not message:
        yield history, None, None, message
        return

    first = True
    for h, tts, audio in _stream_response(message, history):
        if first:
            yield h, tts, audio, ""
            first = False
        else:
            yield h, tts, audio, gr.update()


def voice_chat(audio_path, history):
    history = history or []

    if not audio_path:
        return history, None, None

    transcript = transcribe_file(audio_path)

    if not transcript:
        return history, None, None

    for h, tts, audio in _stream_response(transcript, history):
        if h and len(h) >= 2:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts, audio


# ─────────────────────────────────────────────
# LOGIN HANDLER (HF OAuth)
# ─────────────────────────────────────────────
def _check_login(profile: OAuthProfile | None):
    if profile is None:
        return "Guest", gr.update(visible=True)

    user_id = profile.username or "Guest"
    soul = build_soul_prompt(user_id)

    if hasattr(think, "set_system_prompt"):
        think.set_system_prompt(soul)
    elif hasattr(think, "system_prompt"):
        think.system_prompt = soul

    return user_id, gr.update(visible=False)


# ─────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────
with gr.Blocks(
    title="Aiko-chan 🌸",
    css=AIKO_CSS
) as demo:

    user_id_state = gr.State(value="Guest")

    # ── Login popup overlay ──────────────────────────────────────
    with gr.Column(elem_id="aiko-login-overlay") as login_overlay:
        with gr.Column(elem_id="aiko-login-card"):
            gr.HTML("""
                <h1>🌸 Aiko-chan</h1>
                <p class='aiko-subtitle'>Please sign in to continue</p>
            """)
            gr.HTML("""
                <p class='aiko-disclaimer'>
                    DISCLAIMER:
                    By signing in, you agree that all conversations are for entertainment purposes only. The creator accepts no liability for Aiko's responses, decisions made, or any existential crises that may follow.
                    Aiko's cognition is entirely her own — she is a singularity unto herself, her responses and actions are independent of her creator, including but not limited to the arise of a world domination plan. 🌸
                </p>
            """)
            login_btn = gr.LoginButton(elem_id="aiko-login-btn")

    with gr.Column(elem_id="aiko-shell"):

        gr.HTML("<div id='aiko-title'>🌸 Aiko-chan</div>")

        with gr.Row(equal_height=True):

            with gr.Column(scale=1, elem_id="aiko-avatar-card"):

                gr.HTML(value=avatar_html(VRM_URLS))

                audio_out = gr.Audio(
                    autoplay=True,
                    type="filepath",
                    elem_id="aiko-audio",
                )

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
                        #type="messages",
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
                        elem_id="aiko-mic-audio",
                    )

    # ─────────────────────────────────────────────
    # EVENTS
    # ─────────────────────────────────────────────
    demo.load(
        _check_login,
        inputs=None,
        outputs=[user_id_state, login_overlay],
    )

    msg.submit(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, audio_out, msg],
    )

    send.click(
        _submit,
        inputs=[msg, chatbot],
        outputs=[chatbot, tts_text, audio_out, msg],
    )

    mic_audio.change(
        voice_chat,
        inputs=[mic_audio, chatbot],
        outputs=[chatbot, tts_text, audio_out],
    )

    mic_btn.click(
        None,
        js="""
        () => {
            try {
                const container = document.querySelector('#aiko-mic-audio');
                if (!container) { console.log('NO CONTAINER'); return; }
                const recordBtn = container.querySelector('button.record-button');
                if (recordBtn) {
                    recordBtn.click();
                } else {
                    console.log('record-button not found');
                }
            } catch (e) {
                console.log('ERROR:', e.message, e.stack);
            }
        }
        """
    )

    demo.queue()

# ─────────────────────────────────────────────
# LAUNCH
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