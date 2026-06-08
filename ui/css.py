CSS = """
/* ── Reset & root ── */
html, body, .gradio-container {
    background: #0b1e1d !important;
    color: #dde8e6 !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
}

:root {
    --ak-bg:          #0b1e1d;
    --ak-surface:     #112625;
    --ak-surface2:    #17302e;
    --ak-border:      rgba(110,198,184,0.18);
    --ak-teal:        #4dc4b4;
    --ak-teal-dim:    rgba(77,196,180,0.12);
    --ak-lavender:    #b8a4e8;
    --ak-lav-dim:     rgba(184,164,232,0.14);
    --ak-text:        #dde8e6;
    --ak-text-muted:  rgba(221,232,230,0.55);
    --ak-user-bg:     rgba(138,98,214,0.32);
    --ak-user-border: rgba(184,164,232,0.30);
    --ak-bot-bg:      rgba(77,196,180,0.10);
    --ak-bot-border:  rgba(110,198,184,0.22);
    --ak-radius:      14px;
}

/* ── Hide Gradio chrome ── */
footer, .svelte-1ipelgc,
.gradio-container > .app > .wrap > .gap > .block > .label-wrap,
.block > .label-wrap { display: none !important; }

.app, .wrap, .gap, .form, .panel,
.block, [class*="gradio-"] > div {
    background: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

/* ── Page layout ── */
.gradio-container {
    max-width: 1200px !important;
    min-height: 100vh !important;
    background: var(--ak-bg) !important;
}

/* ── Header ── */
#aiko-header {
    text-align: center;
    padding: 28px 0 8px;
    border-bottom: 1px solid var(--ak-border);
    margin-bottom: 16px;
}
#aiko-header h1 {
    font-size: 1.55rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    color: #a8ddd6 !important;
    margin: 0 !important;
    font-family: 'Georgia', serif !important;
}
#aiko-header p {
    font-size: 0.78rem !important;
    color: var(--ak-text-muted) !important;
    margin: 4px 0 0 !important;
    letter-spacing: 0.04em !important;
}

/* ── Chatbot container ── */
#aiko-chatbot,
#aiko-chatbot > div {
    background: var(--ak-surface) !important;
    border: 1px solid var(--ak-border) !important;
    border-radius: var(--ak-radius) !important;
    height: 500px !important;
    overflow-y: auto !important;
    padding: 12px 8px !important;
}

/* ── Message rows ── */
#aiko-chatbot .message-wrap,
#aiko-chatbot .messages {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    gap: 10px !important;
    display: flex !important;
    flex-direction: column !important;
}

/* ── Individual bubbles — single selector chain, no conflicts ── */
#aiko-chatbot .message {
    padding: 10px 14px !important;
    border-radius: var(--ak-radius) !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    max-width: 80% !important;
    word-wrap: break-word !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* User bubble — right aligned, soft purple */
#aiko-chatbot .message.user {
    background: var(--ak-user-bg) !important;
    border: 1px solid var(--ak-user-border) !important;
    border-radius: 16px 4px 16px 16px !important;
    color: #ede6ff !important;
    margin-left: auto !important;
    margin-right: 8px !important;
}

/* Bot bubble — left aligned, teal tint */
#aiko-chatbot .message.bot,
#aiko-chatbot .message.assistant {
    background: var(--ak-bot-bg) !important;
    border: 1px solid var(--ak-bot-border) !important;
    border-radius: 4px 16px 16px 16px !important;
    color: #d8f0ee !important;
    margin-right: auto !important;
    margin-left: 8px !important;
}

/* Force text color inheritance inside bubbles */
#aiko-chatbot .message.user  * { color: #ede6ff !important; }
#aiko-chatbot .message.bot   * { color: #d8f0ee !important; }
#aiko-chatbot .message.assistant * { color: #d8f0ee !important; }

/* Italic search status line inside bot bubble */
#aiko-chatbot .message.bot em,
#aiko-chatbot .message.assistant em {
    color: var(--ak-teal) !important;
    font-style: italic !important;
    font-size: 0.82rem !important;
    display: block !important;
    margin-bottom: 6px !important;
    opacity: 0.85 !important;
}

/* ── Input area ── */
#aiko-input-row {
    margin-top: 10px !important;
    display: flex !important;
    align-items: center !important;
    gap: 8px !important;
}

#aiko-chatbot + div textarea,
.gradio-container textarea {
    background: var(--ak-surface2) !important;
    border: 1px solid var(--ak-border) !important;
    border-radius: 24px !important;
    color: var(--ak-text) !important;
    caret-color: var(--ak-teal) !important;
    padding: 11px 20px !important;
    font-size: 0.88rem !important;
    resize: none !important;
    line-height: 1.5 !important;
    transition: border-color 0.2s ease !important;
}
.gradio-container textarea:focus {
    border-color: rgba(110,198,184,0.50) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(77,196,180,0.10) !important;
}
.gradio-container textarea::placeholder {
    color: var(--ak-text-muted) !important;
}

/* ── Submit button ── */
button[aria-label="Submit"],
#component-submit-btn {
    background: rgba(77,196,180,0.18) !important;
    border: 1px solid rgba(77,196,180,0.40) !important;
    border-radius: 50% !important;
    color: var(--ak-teal) !important;
    width: 40px !important;
    height: 40px !important;
    padding: 0 !important;
    transition: background 0.2s ease !important;
    flex-shrink: 0 !important;
}
button[aria-label="Submit"]:hover {
    background: rgba(77,196,180,0.30) !important;
}

/* ── Sidebar ── */
#aiko-col {
    padding: 0 0 0 8px !important;
}
#aiko-sidebar {
    background: var(--ak-surface) !important;
    border: 1px solid var(--ak-border) !important;
    border-radius: var(--ak-radius) !important;
    padding: 16px 12px !important;
    height: 100% !important;
}

/* ── Status pill — shown inside bot message for search state ── */
.aiko-status {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    font-size: 0.76rem !important;
    color: var(--ak-teal) !important;
    background: var(--ak-teal-dim) !important;
    border: 1px solid rgba(77,196,180,0.22) !important;
    border-radius: 20px !important;
    padding: 3px 10px !important;
    margin-bottom: 8px !important;
    letter-spacing: 0.02em !important;
}

/* ── Memory badge (sidebar) ── */
.aiko-mem-badge {
    background: var(--ak-lav-dim) !important;
    border: 1px solid rgba(184,164,232,0.22) !important;
    border-radius: 8px !important;
    padding: 8px 12px !important;
    font-size: 0.78rem !important;
    color: var(--ak-lavender) !important;
    margin-bottom: 8px !important;
}

/* ── Scrollbars ── */
* { scrollbar-width: thin; scrollbar-color: rgba(77,196,180,0.30) transparent; }
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(77,196,180,0.30); border-radius: 2px; }

/* ── General text ── */
.gradio-container p,
.gradio-container label,
.gradio-container span { color: var(--ak-text) !important; }

/* ── Layout row gap ── */
.gradio-container .row { gap: 12px !important; }
"""