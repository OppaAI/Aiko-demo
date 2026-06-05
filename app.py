from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup

result = AikoWakeup(text_mode=True).boot(
    on_loading=lambda k: print(f"[boot] {k}"),
    on_done=lambda k: print(f"[boot] done {k}"),
    on_skip=lambda k: print(f"[boot] skip {k}"),
)
think = result.think

def chat(message, history):
    tokens = []
    think.chat(message, token_callback=lambda t: tokens.append(t))
    return "".join(tokens)

demo = gr.ChatInterface(fn=chat, title="Aiko-chan ✨")

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")