AIKO_CSS = """
html, body { background: #080612 !important; color-scheme: dark !important; }
body, .gradio-container { background: #080612 !important; color: #d4c8f0 !important; }
.gradio-container {
    max-width: 1200px !important;
    background:
        radial-gradient(ellipse 80% 60% at 15% 20%, rgba(91,47,168,0.18) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 80%, rgba(155,127,212,0.10) 0%, transparent 55%),
        #080612 !important;
    min-height: 100vh;
}
:root, .dark {
    --body-background-fill: #080612 !important;
    --background-fill-primary: #0d0920 !important;
    --background-fill-secondary: #110d24 !important;
    --color-accent: #9b7fd4 !important;
    --input-background-fill: rgba(15,10,30,0.85) !important;
    --input-border-color: rgba(155,127,212,0.3) !important;
    --border-color-primary: rgba(155,127,212,0.2) !important;
    --color-text-body: #d4c8f0 !important;
    --body-text-color: #d4c8f0 !important;
    --block-label-text-color: rgba(196,168,255,0.8) !important;
}
.app, .wrap, footer, .block, .form, .gap, .panel {
    background: transparent !important;
    border-color: transparent !important;
}
.gradio-container h1 {
    color: #c4a8ff !important;
    font-family: 'Georgia', serif !important;
    letter-spacing: 0.06em !important;
}

/* ── chatbot container ── */
#aiko-chatbot, [data-testid="chatbot"] {
    background: rgba(15,10,30,0.65) !important;
    border: 1px solid rgba(155,127,212,0.2) !important;
    border-radius: 16px !important;
    height: 480px !important;
}
[data-testid="chatbot"] > .label-wrap { display: none !important; }

/* ── message row (parent of each bubble) ── */
[data-testid="message"] {
    display: flex !important;
    width: 100% !important;
    background: transparent !important;
}

/* ── user bubble ── */
[data-testid="user"] {
    background: rgba(0, 80, 90, 0.75) !important;
    border: 1px solid rgba(0, 180, 200, 0.25) !important;
    border-radius: 14px 14px 4px 14px !important;
    color: #c8f4f8 !important;
    max-width: 75% !important;
    width: fit-content !important;
    margin-left: auto !important;
    padding: 10px 14px !important;
    box-sizing: border-box !important;
}

/* ── bot bubble ── */
[data-testid="bot"] {
    background: rgba(91, 47, 168, 0.45) !important;
    border: 1px solid rgba(155, 127, 212, 0.3) !important;
    border-radius: 14px 14px 14px 4px !important;
    color: #e8deff !important;
    max-width: 75% !important;
    width: fit-content !important;
    margin-right: auto !important;
    padding: 10px 14px !important;
    box-sizing: border-box !important;
}

[data-testid="user"] * { color: #c8f4f8 !important; }
[data-testid="bot"] *  { color: #e8deff !important; }

/* ── inputs ── */
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

button[aria-label="Submit"], button[type="submit"] {
    background: linear-gradient(135deg, rgba(91,47,168,0.8), rgba(123,79,212,0.7)) !important;
    border: 1px solid rgba(155,127,212,0.4) !important;
    border-radius: 10px !important;
    color: #f0e8ff !important;
}

.gradio-container button { color: #c4a8ff !important; }
.gradio-container button:hover { color: #e8deff !important; }
.gradio-container label, .gradio-container p, label, p {
    color: rgba(196,168,255,0.8) !important;
}

* { scrollbar-width: thin; scrollbar-color: rgba(123,79,212,0.4) rgba(15,10,30,0.3); }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: rgba(15,10,30,0.3); border-radius: 3px; }
::-webkit-scrollbar-thumb { background: rgba(123,79,212,0.4); border-radius: 3px; }

#aiko-col { padding: 0 !important; }
.gradio-container .row { gap: 16px !important; }
"""