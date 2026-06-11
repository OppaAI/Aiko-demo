from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import gradio as gr
import time

from core.wakeup import AikoWakeup
from ui.css import AIKO_CSS
from ui.asr import transcribe_file
from ui.speak import speak_to_file
from ui.vrm import avatar_html, gradio_file_urls, resolve_vrm_path

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done=lambda k: print(f"[boot]    done: {k}"),
    on_skip=lambda k: print(f"[boot]    skip: {k}"),
)
think = result.think
memorize = result.memorize

if hasattr(think, "join_warmup"):
    think.join_warmup()

VRM_PATH = resolve_vrm_path()
VRM_URLS = gradio_file_urls(VRM_PATH)

try:
    gr.set_static_paths(paths=[VRM_PATH.parent])
except AttributeError:
    pass


def _strip_for_speech(text: str) -> str:
    """Remove markdown/search-status noise so the VRM lip sync gets plain text."""
    import re
    cleaned = re.sub(r"\n?🔍 Searching: \*.*?\*\n?", "", text)
    cleaned = re.sub(r"<think>.*?</think>", "", cleaned, flags=re.DOTALL)
    return cleaned.strip()


import re

_SENTENCE_END = re.compile(r'(?<=[.!?。！？\n])\s*')


def _split_ready_sentences(buffer: str) -> tuple[list[str], str]:
    """Split buffer into complete sentences + remaining partial text."""
    parts = _SENTENCE_END.split(buffer)
    if len(parts) <= 1:
        return [], buffer
    *complete, remainder = parts
    return [p for p in complete if p.strip()], remainder


def _stream_response(message: str, history: list):
    """Generator: yields (history, tts_text, audio_path) — no msg output.

    Immediately emits the user turn so it appears before inference begins,
    then streams assistant tokens sentence-by-sentence for TTS.
    tts_text carries "EMOTION:<name>|<sentence>" so the JS can split and
    drive both lip-sync and facial expression on the VRM.
    """
    # ── 1. Show user message immediately, AI turn shows cursor ───────────
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": "▋"},
    ]
    yield history, "", None

    buffer = ""
    full_text = ""

    def _cb(token):
        nonlocal buffer, full_text
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            note = f"\n🔍 Searching: *{query}*\n"
            buffer += note
            full_text += note
        else:
            buffer += token
            full_text += token

    # ── 2. Run think.chat in background thread ────────────────────────────
    import threading
    done = threading.Event()
    error = {}

    def _run():
        try:
            think.chat(message, token_callback=_cb)
        except Exception as e:
            error["e"] = e
        finally:
            done.set()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    # ── 3. Stream sentences as they complete ─────────────────────────────
    while not done.is_set() or buffer.strip():
        sentences, buffer = _split_ready_sentences(buffer)
        for sentence in sentences:
            clean = _strip_for_speech(sentence)
            if not clean:
                continue
            history[-1]["content"] = full_text + ("▋" if not done.is_set() else "")
            audio, emotion = speak_to_file(clean)
            # Pack emotion into tts_text so the JS can drive the VRM expression
            tts_payload = f"EMOTION:{emotion}|{clean}"
            yield history, tts_payload, audio
        if not sentences:
            if full_text:
                history[-1]["content"] = full_text + "▋"
                yield history, "", None
            time.sleep(0.05)

    # ── 4. Flush trailing partial sentence ───────────────────────────────
    if buffer.strip():
        clean = _strip_for_speech(buffer)
        history[-1]["content"] = full_text
        if clean:
            audio, emotion = speak_to_file(clean)
            tts_payload = f"EMOTION:{emotion}|{clean}"
            yield history, tts_payload, audio
        else:
            yield history, "", None

    if error:
        raise error["e"]

    # ── 5. Final: full text, no cursor ────────────────────────────────────
    history[-1]["content"] = full_text
    yield history, "", None


def text_chat(message: str, history: list):
    """Handle text input. msg is cleared via JS before this runs."""
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
        if h and h[-2]["content"] == transcript:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts, audio


with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS, fill_height=True) as demo:
    with gr.Column(elem_id="aiko-shell"):
        gr.HTML("""
            <div id="aiko-title">🌸 Aiko-chan</div>
            <script>
            (function() {
              function postToVrm(text, emotion) {
                const frame = document.getElementById('aiko-vrm-frame');
                if (!frame) return;
                frame.contentWindow.postMessage(
                  { ttsText: text, playNow: true, expression: emotion || "neutral" },
                  '*'
                );
              }

              function hookAudio() {
                const audio = document.querySelector('#aiko-audio audio');
                if (!audio) { setTimeout(hookAudio, 600); return; }
                ['play', 'playing'].forEach(evt => {
                  audio.addEventListener(evt, () => {
                    setTimeout(() => {
                      const el = document.querySelector('#aiko-tts-text textarea');
                      if (!el || !el.value) return;
                      const raw = el.value;
                      const emotionMatch = raw.match(/^EMOTION:([^|]+)\|(.*)$/s);
                      if (emotionMatch) {
                        postToVrm(emotionMatch[2].trim(), emotionMatch[1].trim());
                      } else {
                        postToVrm(raw, "neutral");
                      }
                    }, 150);
                  });
                });
              }

              function watchTtsText() {
                const container = document.querySelector('#aiko-tts-text');
                if (!container) { setTimeout(watchTtsText, 600); return; }
                const observer = new MutationObserver(() => {
                  const el = container.querySelector('textarea');
                  if (!el || !el.value) return;
                  const raw = el.value;
                  // Parse "EMOTION:<name>|<tts text>" payload
                  const emotionMatch = raw.match(/^EMOTION:([^|]+)\|(.*)$/s);
                  if (emotionMatch) {
                    const emotion = emotionMatch[1].trim();
                    const ttsText = emotionMatch[2].trim();
                    postToVrm(ttsText, emotion);
                  } else {
                    postToVrm(raw, "neutral");
                  }
                });
                observer.observe(container, { childList: true, subtree: true, characterData: true, attributes: true });
              }

              // Hook mic button to show + click the hidden gr.Audio recorder
              function hookMicBtn() {
                const btn = document.querySelector('#aiko-mic-btn button');
                const recorderWrap = document.querySelector('#aiko-mic-audio');
                if (!btn || !recorderWrap) { setTimeout(hookMicBtn, 600); return; }

                // Make the hidden recorder visible but off-screen so Gradio renders it
                recorderWrap.style.position = 'fixed';
                recorderWrap.style.opacity = '0';
                recorderWrap.style.pointerEvents = 'none';
                recorderWrap.style.display = 'block';

                btn.addEventListener('click', () => {
                  // Find and click the actual record button inside the hidden Audio
                  const recBtn = recorderWrap.querySelector('button');
                  if (recBtn) recBtn.click();
                });
              }

              setTimeout(() => { hookAudio(); watchTtsText(); hookMicBtn(); }, 1200);
            })();
            </script>
            """)

        with gr.Row(equal_height=True):
            with gr.Column(scale=1, elem_id="aiko-avatar-card"):
                gr.HTML(value=avatar_html(VRM_URLS), show_label=False)
                audio_out = gr.Audio(
                    autoplay=True, visible=True, label="🔊 Aiko",
                    type="filepath", elem_id="aiko-audio", container=False,
                )
                tts_text = gr.Textbox(value="", visible=False, elem_id="aiko-tts-text", render=True)

                with gr.Column(elem_id="aiko-chat-overlay"):
                    chatbot = gr.Chatbot(
                        elem_id="aiko-chatbot",
                        show_label=False,
                        height=600,
                        type="messages",
                    )

                with gr.Row(elem_id="aiko-input-row"):
                    # Plain emoji button — JS hooks its click to start the hidden recorder
                    mic_btn = gr.Button("🎙️", scale=0, elem_id="aiko-mic-btn", min_width=0)
                    msg = gr.Textbox(
                        placeholder="Type a message…",
                        show_label=False,
                        scale=12,
                        container=False,
                        elem_id="aiko-msg",
                    )
                    send = gr.Button("➤", variant="primary", scale=0, elem_id="aiko-send", min_width=0)

                # Hidden recorder — JS shows and activates it when mic_btn is clicked
                mic_audio = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="",
                    elem_id="aiko-mic-audio",
                    container=False,
                    show_label=False,
                    visible=False,
                )

                # ── Two-step submit: clear box immediately, then stream ──────
                pending = gr.State("")

                def _capture_and_clear(message):
                    """Capture the message and return a cleared textbox immediately."""
                    return (message or "").strip(), gr.update(value="")

                def _stream_from_state(message, history):
                    yield from text_chat(message, history)

                for trigger in (msg.submit, send.click):
                    trigger(
                        _capture_and_clear,
                        inputs=[msg],
                        outputs=[pending, msg],
                        queue=False,
                    ).then(
                        _stream_from_state,
                        inputs=[pending, chatbot],
                        outputs=[chatbot, tts_text, audio_out],
                    )

                mic_audio.change(voice_chat, [mic_audio, chatbot], [chatbot, tts_text, audio_out])

allowed_paths = [str(Path("/tmp/aiko_tts")), str(VRM_PATH.parent)]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)