"""
app.py — Aiko-chan HF Space entry point (replaces main.py + tui/)
"""
from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup, BootResult

# ── boot (once at Space startup) ──────────────────────────────────────────────

result: BootResult = AikoWakeup(text_mode=True).boot(  # text_mode until ASR wired
    on_loading = lambda k: print(f"[boot] loading: {k}"),
    on_done    = lambda k: print(f"[boot]    done: {k}"),
    on_skip    = lambda k: print(f"[boot]    skip: {k}"),
)
think    = result.think
memorize = result.memorize
speak    = result.speak
listen   = result.listen


# ── chat handler ──────────────────────────────────────────────────────────────

def chat(message: str, history: list):
    tokens = []
    def _cb(token): tokens.append(token)
    think.chat(message, token_callback=_cb)
    return "".join(tokens)


def reset():
    think.reset_context()
    return [], "Context cleared."


# ── gradio ui ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="Aiko-chan") as demo:
    gr.Markdown("# Aiko-chan ✨")
    chatbot  = gr.Chatbot(type="messages")
    with gr.Row():
        txt_in = gr.Textbox(placeholder="Talk to Aiko...", scale=9)
        send   = gr.Button("Send", scale=1)
    reset_btn = gr.Button("Reset Context")
    status    = gr.Textbox(label="Status", interactive=False)

    send.click(
        fn=lambda msg, hist: (hist + [{"role":"user","content":msg},
                                      {"role":"assistant","content":chat(msg, hist)}], ""),
        inputs=[txt_in, chatbot], outputs=[chatbot, txt_in]
    )
    reset_btn.click(fn=reset, outputs=[chatbot, status])


if __name__ == "__main__":
    demo.launch()