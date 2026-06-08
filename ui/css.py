CSS = """
/* ── Base ── */
html, body {
    background: #0d2c2e !important;
    color-scheme: dark !important;
}
body, .gradio-container {
    background: #0d2c2e !important;
    color: #e8e0f5 !important;
}
.gradio-container {
    max-width: 1200px !important;
    background:
        radial-gradient(ellipse 70% 60% at 10% 15%, rgba(32,100,90,0.30) 0%, transparent 55%),
        radial-gradient(ellipse 55% 55% at 88% 85%, rgba(155,120,210,0.18) 0%, transparent 55%),
        #0d2c2e !important;
    min-height: 100vh;
}

/* ── CSS Variables ── */
:root, .dark {
    --body-background-fill:       #0d2c2e !important;
    --background-fill-primary:    rgba(18,55,52,0.85) !important;
    --background-fill-secondary:  rgba(25,65,62,0.70) !important;
    --color-accent:               #6ec6b8 !important;
    --neutral-950:                #e8e0f5 !important;
    --neutral-900:                #d4cbec !important;
    --neutral-800:                #bfb5e0 !important;
    --neutral-100:                #1a3835 !important;
    --neutral-50:                 #122f2d !important;
    --input-background-fill:      rgba(220,210,245,0.12) !important;
    --input-border-color:         rgba(110,198,184,0.35) !important;
    --chatbot-background:         rgba(230,218,255,0.08) !important;
    --border-color-primary:       rgba(110,198,184,0.20) !important;
    --color-text-body:            #e8e0f5 !important;
    --body-text-color:            #e8e0f5 !important;
    --block-label-text-color:     rgba(174,230,224,0.85) !important;
}

/* ── Transparent chrome ── */
.app, .wrap, footer,
.svelte-1ipelgc, .svelte-byatnx,
[class*="gradio-"] > div,
.block, .form, .gap, .panel {
    background: transparent !important;
    border-color: transparent !important;
}

/* ── Heading ── */
.gradio-container h1 {
    color: #aee6e0 !important;
    font-family: 'Georgia', serif !important;
    letter-spacing: 0.05em !important;
}

/* ── Chatbot window: lavender frosted glass ── */
#aiko-chatbot,
.chatbot,
[data-testid="chatbot"] {
    background: linear-gradient(
        145deg,
        rgba(195,178,240,0.18) 0%,
        rgba(160,220,215,0.10) 60%,
        rgba(185,165,235,0.14) 100%
    ) !important;
    border: 1px solid rgba(174,230,224,0.22) !important;
    border-radius: 18px !important;
    height: 480px !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
}

/* ── User bubble: soft purple pill (right-side) ── */
.message.user, [data-testid="user"],
.bubble-wrap.user .bubble {
    background: rgba(155,110,220,0.45) !important;
    border: 1px solid rgba(195,170,240,0.35) !important;
    border-radius: 18px 18px 4px 18px !important;
    color: #f0e8ff !important;
}

/* ── Bot bubble: mint-tinted frosted glass (left-side) ── */
.message.bot, [data-testid="bot"],
.bubble-wrap.bot .bubble {
    background: rgba(230,245,245,0.14) !important;
    border: 1px solid rgba(130,210,200,0.22) !important;
    border-radius: 18px 18px 18px 4px !important;
    color: #e8f5f4 !important;
}

/* ── Color inheritance ── */
.chatbot *, [data-testid="chatbot"] * { color: inherit !important; }
.message.user *, .bubble-wrap.user * { color: #f0e8ff !important; }
.message.bot *,  .bubble-wrap.bot *  { color: #e8f5f4 !important; }

/* ── Input row: frosted pill ── */
.gradio-container textarea,
.gradio-container input[type="text"],
textarea, input[type="text"] {
    background: rgba(220,235,240,0.10) !important;
    border: 1px solid rgba(110,198,184,0.30) !important;
    border-radius: 24px !important;
    color: #e8f5f4 !important;
    caret-color: #6ec6b8 !important;
    padding: 10px 48px 10px 18px !important;
}
textarea:focus, input[type="text"]:focus {
    border-color: rgba(110,198,184,0.60) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(110,198,184,0.14) !important;
}
textarea::placeholder { color: rgba(174,230,224,0.45) !important; }

/* ── Submit / Send button: teal ── */
button[aria-label="Submit"],
button.submit,
#component-submit-btn,
button[type="submit"] {
    background: linear-gradient(135deg, rgba(32,130,120,0.85), rgba(70,180,168,0.75)) !important;
    border: 1px solid rgba(110,198,184,0.45) !important;
    border-radius: 50% !important;
    color: #e0faf8 !important;
    width: 38px !important;
    height: 38px !important;
}
button[aria-label="Submit"]:hover {
    background: linear-gradient(135deg, rgba(70,180,168,0.95), rgba(110,198,184,0.85)) !important;
}

/* ── ASR (mic) button — place next to the input ── */
#aiko-asr-btn,
button[aria-label="ASR"],
button.asr-btn {
    background: rgba(195,178,240,0.20) !important;
    border: 1px solid rgba(155,127,212,0.40) !important;
    border-radius: 50% !important;
    color: #c4a8ff !important;
    width: 38px !important;
    height: 38px !important;
    transition: background 0.2s ease !important;
}
#aiko-asr-btn:hover,
button[aria-label="ASR"]:hover,
button.asr-btn:hover {
    background: rgba(155,110,220,0.40) !important;
    color: #f0e8ff !important;
}
#aiko-asr-btn.recording,
button[aria-label="ASR"].recording,
button.asr-btn.recording {
    background: rgba(220,80,80,0.40) !important;
    border-color: rgba(255,120,120,0.50) !important;
    color: #ffd0d0 !important;
    animation: pulse-mic 1.2s ease-in-out infinite !important;
}
@keyframes pulse-mic {
    0%, 100% { box-shadow: 0 0 0 0   rgba(220,80,80,0.4); }
    50%       { box-shadow: 0 0 0 8px rgba(220,80,80,0.0); }
}

/* ── General buttons & labels ── */
.gradio-container button       { color: #aee6e0 !important; }
.gradio-container button:hover { color: #e8f5f4 !important; }
.gradio-container label,
.gradio-container .label-wrap span,
.gradio-container p,
label, p { color: rgba(174,230,224,0.85) !important; }

/* ── Sidebar accent column (if using Column with elem_id="aiko-sidebar") ── */
#aiko-sidebar {
    background: rgba(14,52,48,0.70) !important;
    border-right: 1px solid rgba(110,198,184,0.18) !important;
    border-radius: 16px !important;
    padding: 12px 8px !important;
}

/* ── Contact / session list items ── */
.aiko-contact-item {
    background: rgba(230,245,243,0.07) !important;
    border: 1px solid rgba(110,198,184,0.12) !important;
    border-radius: 12px !important;
    padding: 8px 12px !important;
    margin-bottom: 6px !important;
    cursor: pointer !important;
    transition: background 0.15s ease !important;
}
.aiko-contact-item:hover,
.aiko-contact-item.active {
    background: rgba(155,110,220,0.25) !important;
    border-color: rgba(155,127,212,0.35) !important;
}

/* ── Scrollbars ── */
* { scrollbar-width: thin; scrollbar-color: rgba(110,198,184,0.40) rgba(18,55,52,0.30); }
::-webkit-scrollbar       { width: 5px; }
::-webkit-scrollbar-track { background: rgba(18,55,52,0.30); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: rgba(110,198,184,0.40); border-radius: 3px; }

/* ── Layout ── */
#aiko-col { padding: 0 !important; }
.gradio-container .row { gap: 16px !important; }
"""

# ── Gradio layout snippet showing how to add the ASR button ──────────────────
#
# In your gr.Blocks() layout, place the mic button in the same Row as your
# chat input. Example:
#
#   with gr.Row(elem_id="aiko-input-row"):
#       asr_btn = gr.Button("🎤", elem_id="aiko-asr-btn", scale=0, min_width=44)
#       chat_input = gr.Textbox(
#           placeholder="Type here...",
#           show_label=False,
#           scale=10,
#           container=False,
#       )
#       send_btn = gr.Button("➤", elem_id="aiko-send-btn", scale=0, min_width=44)
#
# Wire up the ASR button with a click handler:
#
#   asr_btn.click(fn=start_asr_or_stop, outputs=chat_input)
#
# The CSS above targets #aiko-asr-btn for idle styling and adds a
# `.recording` class pulse animation for active ASR state (toggle via JS
# or by returning updated elem_classes from your callback).
# ─────────────────────────────────────────────────────────────────────────────