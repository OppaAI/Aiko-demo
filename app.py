from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup
from ui.css import CSS
from ui.speech import SPEECH_JS
from ui.vrm_viewer import VRM_VIEWER

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] loading: {k}"),
    on_done   =lambda k: print(f"[boot]    done: {k}"),
    on_skip   =lambda k: print(f"[boot]    skip: {k}"),
)
think    = result.think
memorize = result.memorize

if hasattr(think, "join_warmup"):
    think.join_warmup()


def chat(message, history):
    tokens = []
    def _cb(token):
        if token.startswith("__SEARCHING__:"):
            query = token.split(":", 1)[1].strip()
            tokens.append(f"\n🔍 Searching: *{query}*\n")
        else:
            tokens.append(token)
    think.chat(message, token_callback=_cb)
    return "".join(tokens)


with gr.Blocks(title="Aiko-chan 🌸", css=CSS, theme=gr.themes.Base()) as demo:
    gr.HTML(SPEECH_JS)

    with gr.Row(elem_id="aiko-main-row"):
        with gr.Column(scale=6, elem_id="aiko-chat-col"):
            chatbot = gr.Chatbot(
                elem_id="aiko-chatbot",
                height="100%",
            )
            
            gr.ChatInterface(
                fn=chat,
                chatbot=chatbot,
                title="Aiko-chan 🌸",
                textbox=gr.Textbox(
                    placeholder="Say something to Aiko-chan...",
                    container=False,
                    scale=7,
                ),
                submit_btn=gr.Button("Send 💌", variant="primary", scale=1),
                stop_btn=gr.Button("Stop ✋", variant="stop", scale=1),
                examples=[
                    "Tell me about yourself",
                    "What's on your mind?",
                    "Can you search for something?",
                ],
            )
        with gr.Column(scale=4, elem_id="aiko-vrm-col"):
            gr.HTML(VRM_VIEWER)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=["static"],
)