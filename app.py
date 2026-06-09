from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from core.wakeup import AikoWakeup

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
            tokens.append(f"\n\U0001f50d Searching: *{query}*\n")
        else:
            tokens.append(token)
    think.chat(message, token_callback=_cb)
    return "".join(tokens)


# ── dark lavender glassmorphic CSS ────────────────────────────────────────────
_CSS = """
html, body {
    background: #080612 !important;
    color-scheme: dark !important;
}
body, .gradio-container {
    background: #080612 !important;
    color: #d4c8f0 !important;
}
.gradio-container {
    max-width: 1200px !important;
    background:
        radial-gradient(ellipse 80% 60% at 15% 20%, rgba(91,47,168,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 80%, rgba(155,127,212,0.10) 0%, transparent 55%),
        #080612 !important;
    min-height: 100vh;
}

/* Force dark on Gradio's theme root vars */
:root, .dark {
    --body-background-fill: #080612 !important;
    --background-fill-primary: #0d0920 !important;
    --background-fill-secondary: #110d24 !important;
    --color-accent: #9b7fd4 !important;
    --neutral-950: #d4c8f0 !important;
    --neutral-900: #c4b8e0 !important;
    --neutral-800: #b4a8d0 !important;
    --neutral-100: #1a1030 !important;
    --neutral-50: #0d0920 !important;
    --input-background-fill: rgba(15,10,30,0.85) !important;
    --input-border-color: rgba(155,127,212,0.3) !important;
    --chatbot-background: rgba(10,7,20,0.8) !important;
    --border-color-primary: rgba(155,127,212,0.2) !important;
    --color-text-body: #d4c8f0 !important;
    --body-text-color: #d4c8f0 !important;
    --block-label-text-color: rgba(196,168,255,0.8) !important;
}

/* Nuke any white panels Gradio injects */
.app, .wrap, footer,
.svelte-1ipelgc, .svelte-byatnx,
[class*="gradio-"] > div,
.block, .form, .gap, .panel {
    background: transparent !important;
    border-color: transparent !important;
}

/* Chat panel */
.gradio-container h1 {
    color: #c4a8ff !important;
    font-family: 'Georgia', serif !important;
    letter-spacing: 0.06em !important;
}

#aiko-chatbot,
.chatbot,
[data-testid="chatbot"] {
    background: rgba(15,10,30,0.65) !important;
    border: 1px solid rgba(155,127,212,0.2) !important;
    border-radius: 16px !important;
    height: 480px !important;
}

/* Message bubbles */
.message.user, [data-testid="user"],
.bubble-wrap.user .bubble {
    background: rgba(91,47,168,0.35) !important;
    border: 1px solid rgba(155,127,212,0.25) !important;
    border-radius: 14px 14px 4px 14px !important;
    color: #e8deff !important;
}
.message.bot, [data-testid="bot"],
.bubble-wrap.bot .bubble {
    background: rgba(20,12,42,0.6) !important;
    border: 1px solid rgba(155,127,212,0.15) !important;
    border-radius: 14px 14px 14px 4px !important;
    color: #d4c8f0 !important;
}

/* Ensure all text inside chatbot is bright enough */
.chatbot *, [data-testid="chatbot"] * {
    color: inherit !important;
}
.message.user *, .bubble-wrap.user * { color: #e8deff !important; }
.message.bot *, .bubble-wrap.bot * { color: #d4c8f0 !important; }

/* Input box */
.gradio-container textarea,
.gradio-container input[type="text"],
textarea, input[type="text"] {
    background: rgba(15,10,30,0.85) !important;
    border: 1px solid rgba(155,127,212,0.25) !important;
    border-radius: 12px !important;
    color: #e8deff !important;
    caret-color: #9b7fd4 !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: rgba(155,127,212,0.5) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(123,79,212,0.15) !important;
}
textarea::placeholder { color: rgba(155,127,212,0.4) !important; }

/* Submit button */
button[aria-label="Submit"],
button.submit,
#component-submit-btn,
button[type="submit"] {
    background: linear-gradient(135deg, rgba(91,47,168,0.8), rgba(123,79,212,0.7)) !important;
    border: 1px solid rgba(155,127,212,0.4) !important;
    border-radius: 10px !important;
    color: #f0e8ff !important;
}
button[aria-label="Submit"]:hover { background: linear-gradient(135deg, rgba(123,79,212,0.9), rgba(155,127,212,0.8)) !important; }

/* All other buttons and labels */
.gradio-container button { color: #c4a8ff !important; }
.gradio-container button:hover { color: #e8deff !important; }
.gradio-container label,
.gradio-container .label-wrap span,
.gradio-container p,
label, p { color: rgba(196,168,255,0.8) !important; }

/* Scrollbars */
* { scrollbar-width: thin; scrollbar-color: rgba(123,79,212,0.4) rgba(15,10,30,0.3); }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: rgba(15,10,30,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: rgba(123,79,212,0.4); border-radius: 3px; }

#aiko-col { padding: 0 !important; }
.gradio-container .row { gap: 16px !important; }
"""

# ── gradio ui ─────────────────────────────────────────────────────────────────
with gr.Blocks(title="Aiko-chan \U0001f338", css=_CSS) as demo:
    gr.HTML(_SPEECH_JS)

    with gr.Row():
        with gr.Column(scale=6):
            gr.ChatInterface(
                fn=chat,
                title="Aiko-chan \U0001f338",
                chatbot=gr.Chatbot(elem_id="aiko-chatbot"),
            )
        with gr.Column(scale=4, elem_id="aiko-col"):
            gr.HTML(_VRM_VIEWER)

demo.launch(
    server_name="0.0.0.0",
    server_port=7860,
    ssr_mode=False,
    share=False,   # HF Spaces handles routing; share=True only needed for local tunneling
)