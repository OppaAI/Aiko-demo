from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import gradio as gr

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


def _assistant_response(message: str) -> tuple[str, str | None]:
    tokens: list[str] = []

    def _cb(token):
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            tokens.append(f"\n🔍 Searching: *{query}*\n")
        else:
            tokens.append(token)

    think.chat(message, token_callback=_cb)
    text = "".join(tokens)
    audio = speak_to_file(text)
    print(f"[chat] audio path: {audio}")
    return text, audio


def text_chat(message, history):
    history = history or []
    message = (message or "").strip()
    if not message:
        return history, None, ""
    text, audio = _assistant_response(message)
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": text})
    return history, audio, ""


def voice_chat(audio_path, history):
    history = history or []
    if not audio_path:
        return history, None, None
    transcript = transcribe_file(audio_path)
    if not transcript:
        return history, None, None
    text, audio = _assistant_response(transcript)
    history.append({"role": "user", "content": f"🎙️ {transcript}"})
    history.append({"role": "assistant", "content": text})
    return history, audio, None


with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS, fill_height=True) as demo:
    with gr.Column(elem_id="aiko-shell"):
        with gr.Row(equal_height=True):
            with gr.Column(scale=5, elem_id="aiko-avatar-card"):
                gr.HTML(value=avatar_html(VRM_URLS), show_label=False)
                audio_out = gr.Audio(
                    autoplay=True,
                    visible=True,
                    label="🔊 Aiko",
                    type="filepath",
                    elem_id="aiko-audio",
                    container=False,
                )
                gr.Markdown(
                    "Aiko's VRM mouth is driven by the MP3 playback level in your browser.",
                    elem_id="aiko-note",
                )
            with gr.Column(scale=6, elem_id="aiko-chat-card"):
                gr.Markdown("# Aiko-chan 🌸", elem_id="aiko-title")
                chatbot = gr.Chatbot(
                    elem_id="aiko-chatbot",
                    show_label=False,
                    height=520,
                    #type="messages",
                )
                with gr.Row(elem_id="aiko-input-row"):
                    msg = gr.Textbox(
                        placeholder="Type a message…",
                        show_label=False,
                        scale=12,
                        container=False,
                    )
                    send = gr.Button("➤", variant="primary", scale=1, elem_id="aiko-send")
                voice_in = gr.Audio(
                    sources=["microphone"],
                    type="filepath",
                    label="🎙️ Speak to Aiko",
                    elem_id="aiko-mic",
                )

                msg.submit(text_chat, [msg, chatbot], [chatbot, audio_out, msg])
                send.click(text_chat, [msg, chatbot], [chatbot, audio_out, msg])
                voice_in.change(voice_chat, [voice_in, chatbot], [chatbot, audio_out, voice_in])

allowed_paths = [str(Path("/tmp/aiko_tts")), str(VRM_PATH.parent)]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)