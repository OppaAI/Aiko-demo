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


# ── Header HTML ──
HEADER_HTML = """
<div id="aiko-header">
    <div class="header-avatar">🌸</div>
    <div class="header-text">
        <h1>Aiko-chan</h1>
        <p class="header-status">
            <span class="status-dot"></span>
            Online · Ready to chat
        </p>
    </div>
</div>
"""

# ── Welcome screen (shown when no messages) ──
WELCOME_HTML = """
<div class="aiko-welcome">
    <div class="welcome-icon">🌸</div>
    <h2>Hi, I'm Aiko!</h2>
    <p>Your personal AI assistant. Ask me anything — I can search the web, remember our conversations, and help you out.</p>
    <div class="suggestion-chips">
        <span class="chip">✨ Tell me about yourself</span>
        <span class="chip">🔍 Search for something</span>
        <span class="chip">💡 Help me brainstorm</span>
        <span class="chip">📝 Summarize a topic</span>
    </div>
</div>
"""


with gr.Blocks(title="Aiko-chan 🌸", css=CSS) as demo:
    gr.HTML(SPEECH_JS)

    # ── Header ──
    gr.HTML(HEADER_HTML)

    with gr.Row(equal_height=True):
        # ── Chat column ──
        with gr.Column(scale=6, min_width=400):
            gr.ChatInterface(
                fn=chat,
                chatbot=gr.Chatbot(
                    elem_id="aiko-chatbot",
                    show_label=False,
                    show_copy_button=True,
                    layout="bubble",
                    bubble_full_width=False,
                    placeholder=WELCOME_HTML,
                ),
                textbox=gr.Textbox(
                    placeholder="Message Aiko-chan...",
                    show_label=False,
                    container=False,
                    elem_id="aiko-input-wrap",
                    scale=9,
                ),
                submit_btn=gr.Button(
                    "➤",
                    variant="primary",
                    elem_id="aiko-send-btn",
                    scale=1,
                ),
                retry_btn=None,
                undo_btn=None,
                clear_btn=gr.Button(
                    "✕ Clear",
                    variant="secondary",
                    size="sm",
                ),
            )

        # ── VRM Viewer column ──
        with gr.Column(scale=4, elem_id="aiko-col", min_width=300):
            gr.HTML(VRM_VIEWER)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,
    allowed_paths=["static"],
)