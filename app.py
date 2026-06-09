from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup
from ui.css import AIKO_CSS
from ui.speak import speak_to_array

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
    text  = "".join(tokens)
    audio = speak_to_array(text)   # (24000, np.ndarray) or None
    return text, audio


with gr.Blocks(title="Aiko-chan 🌸", css=AIKO_CSS) as demo:
    audio_out = gr.Audio(
        autoplay=True,
        visible=False,
        label="voice",
        type="numpy",
    )
    gr.ChatInterface(
        fn=chat,
        title="Aiko-chan 🌸",
        chatbot=gr.Chatbot(
            elem_id="aiko-chatbot",
            show_label=False,
        ),
        additional_outputs=[audio_out],
    )

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
)