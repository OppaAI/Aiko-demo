from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import gradio as gr

from core.wakeup import AikoWakeup
from ui.css import AIKO_CSS
from ui.speak import speak_to_file
from ui.vrm import avatar_html, gradio_file_url, resolve_vrm_path

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
VRM_URL = gradio_file_url(VRM_PATH)

try:
    gr.set_static_paths(paths=[VRM_PATH.parent])
except AttributeError:
    # Older Gradio builds only use launch(allowed_paths=...).
    pass


def chat(message, history):
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
    yield text, audio


with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS) as demo:
    with gr.Column(elem_id="aiko-shell"):
        with gr.Row(equal_height=True):
            with gr.Column(scale=5, elem_id="aiko-avatar-card"):
                gr.HTML(value=avatar_html(VRM_URL), show_label=False)
                audio_out = gr.Audio(
                    autoplay=True,
                    visible=True,
                    label="🔊 Aiko",
                    type="filepath",
                    elem_id="aiko-audio",
                )
                gr.Markdown(
                    "Aiko's VRM mouth is driven by the MP3 playback level in your browser.",
                    elem_id="aiko-note",
                )
            with gr.Column(scale=6, elem_id="aiko-chat-card"):
                gr.ChatInterface(
                    fn=chat,
                    title="Aiko-chan 🌸",
                    chatbot=gr.Chatbot(elem_id="aiko-chatbot", show_label=False),
                    additional_outputs=[audio_out],
                )

allowed_paths = [str(Path("/tmp/aiko_tts")), str(VRM_PATH.parent)]

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=allowed_paths,
)