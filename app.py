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
    # Older Gradio builds only use launch(allowed_paths=...).
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
    """Generator: yields (history, tts_text, audio_path, msg_clear) chunks."""
    buffer = ""
    full_text = ""

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]

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

    # Run think.chat in a background thread so we can poll/yield as it streams
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

    last_yield_len = 0
    while not done.is_set() or buffer.strip():
        sentences, buffer = _split_ready_sentences(buffer)
        for sentence in sentences:
            clean = _strip_for_speech(sentence)
            if not clean:
                continue
            history[-1]["content"] = full_text
            audio = speak_to_file(clean)
            yield history, clean, audio, ""
        if not sentences:
            time.sleep(0.05)

    # Flush any trailing partial sentence
    if buffer.strip():
        clean = _strip_for_speech(buffer)
        history[-1]["content"] = full_text
        if clean:
            audio = speak_to_file(clean)
            yield history, clean, audio, ""
        else:
            yield history, "", None, ""

    if error:
        raise error["e"]

    # Final sync: ensure full text shown
    history[-1]["content"] = full_text
    yield history, "", None, ""


def text_chat(message, history):
    history = history or []
    message = (message or "").strip()
    if not message:
        yield history, None, None, ""
        return
    yield from _stream_response(message, history)


def voice_chat(audio_path, history):
    history = history or []
    if not audio_path:
        yield history, None, None, None
        return
    transcript = transcribe_file(audio_path)
    if not transcript:
        yield history, None, None, None
        return
    history = history  # _stream_response appends user/assistant
    gen = _stream_response(transcript, history)
    for h, tts, audio, _ in gen:
        # patch user message to show mic emoji
        if h and h[-2]["content"] == transcript:
            h[-2]["content"] = f"🎙️ {transcript}"
        yield h, tts, audio, None

with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS, fill_height=True) as demo:
    with gr.Column(elem_id="aiko-shell"):
        gr.HTML("""
            <script>
            (function() {
              function postToVrm(text) {
                const frame = document.getElementById('aiko-vrm-frame');
                if (!frame) return;
                frame.contentWindow.postMessage({ ttsText: text, playNow: true }, '*');
              }
            
              function hookAudio() {
                const audio = document.querySelector('#aiko-audio audio');
                if (!audio) { setTimeout(hookAudio, 600); return; }
                ['play', 'playing'].forEach(evt => {
                  audio.addEventListener(evt, () => {
                    setTimeout(() => {
                      const el = document.querySelector('#aiko-tts-text textarea');
                      if (el && el.value) postToVrm(el.value);
                    }, 150);
                  });
                });
              }
            
              function watchTtsText() {
                const container = document.querySelector('#aiko-tts-text');
                if (!container) { setTimeout(watchTtsText, 600); return; }
                const observer = new MutationObserver(() => {
                  const el = container.querySelector('textarea');
                  if (el && el.value) postToVrm(el.value);
                });
                observer.observe(container, { childList: true, subtree: true, characterData: true, attributes: true });
              }
            
              setTimeout(() => { hookAudio(); watchTtsText(); }, 1200);
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
                    )
        
                with gr.Row(elem_id="aiko-input-row"):
                    msg = gr.Textbox(placeholder="Type a message…", show_label=False, scale=12, container=False)
                    send = gr.Button("➤", variant="primary", scale=1, elem_id="aiko-send")
        
                voice_in = gr.Audio(
                    sources=["microphone"], type="filepath",
                    label="🎙️ Speak to Aiko", elem_id="aiko-mic",
                )

                msg.submit(text_chat, [msg, chatbot], [chatbot, tts_text, audio_out, msg])
                send.click(text_chat, [msg, chatbot], [chatbot, tts_text, audio_out, msg])
                voice_in.change(voice_chat, [voice_in, chatbot], [chatbot, tts_text, audio_out, voice_in])

allowed_paths = [str(Path("/tmp/aiko_tts")), str(VRM_PATH.parent)]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)