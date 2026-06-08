# ui/css.py
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Playfair+Display:wght@400;600&display=swap');

html, body {
    background: #080612 !important;
    color-scheme: dark !important;
    font-family: 'Inter', -apple-system, sans-serif;
}

body, .gradio-container {
    background: #080612 !important;
    color: #d4c8f0 !important;
}

.gradio-container {
    max-width: 1400px !important;
    padding: 24px !important;
    background:
        radial-gradient(ellipse 80% 60% at 15% 20%, rgba(91,47,168,0.15) 0%, transparent 60%),
        radial-gradient(ellipse 60% 50% at 85% 80%, rgba(155,127,212,0.08) 0%, transparent 55%),
        #080612 !important;
    min-height: 100vh;
}

/* ── Main layout ─────────────────────────────────────────── */
#aiko-main-row {
    min-height: 85vh !important;
    align-items: stretch !important;
}

#aiko-chat-col, #aiko-vrm-col {
    display: flex !important;
    flex-direction: column !important;
    height: 85vh !important;
}

#aiko-vrm-col {
    padding: 0 !important;
    border-radius: 20px !important;
    overflow: hidden !important;
}

/* ── Chatbot ───────────────────────────────────────────── */
#aiko-chatbot,
.chatbot,
[data-testid="chatbot"] {
    background: rgba(15,10,30,0.5) !important;
    border: 1px solid rgba(155,127,212,0.18) !important;
    border-radius: 20px !important;
    height: 100% !important;
    max-height: none !important;
    backdrop-filter: blur(10px) !important;
    box-shadow: 
        0 8px 32px rgba(0,0,0,0.2),
        inset 0 1px 0 rgba(255,255,255,0.05) !important;
}

/* Scrollable area inside chatbot */
.chatbot .scroll-hide,
[data-testid="chatbot"] > div:first-child,
.chatbot > .wrap {
    height: 100% !important;
    overflow-y: auto !important;
}

/* ── Narrow bubble widths (replaces bubble_full_width) ───── */
.message.user, .bubble-wrap.user,
[data-testid="user"] {
    margin-left: auto !important;
    margin-right: 8px !important;
    max-width: 80% !important;
    width: auto !important;
}
.message.bot, .bubble-wrap.bot,
[data-testid="bot"] {
    margin-right: auto !important;
    margin-left: 8px !important;
    max-width: 80% !important;
    width: auto !important;
}

/* Messages */
.message.user, [data-testid="user"],
.bubble-wrap.user .bubble {
    background: linear-gradient(135deg, rgba(91,47,168,0.4), rgba(123,79,212,0.3)) !important;
    border: 1px solid rgba(155,127,212,0.25) !important;
    border-radius: 18px 18px 4px 18px !important;
    color: #f0e8ff !important;
    box-shadow: 0 2px 8px rgba(91,47,168,0.15) !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}

.message.bot, [data-testid="bot"],
.bubble-wrap.bot .bubble {
    background: rgba(20,12,42,0.55) !important;
    border: 1px solid rgba(155,127,212,0.15) !important;
    border-radius: 18px 18px 18px 4px !important;
    color: #d4c8f0 !important;
    padding: 12px 16px !important;
    font-size: 14px !important;
    line-height: 1.6 !important;
}

/* Avatar styling */
.message.user .avatar, .message.bot .avatar {
    border: 2px solid rgba(155,127,212,0.3) !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.2) !important;
}

/* ── Input area ────────────────────────────────────────── */
.gradio-container textarea,
.gradio-container input[type="text"],
textarea, input[type="text"] {
    background: rgba(15,10,30,0.7) !important;
    border: 1px solid rgba(155,127,212,0.25) !important;
    border-radius: 14px !important;
    color: #f0e8ff !important;
    caret-color: #c4a8ff !important;
    font-size: 14px !important;
    padding: 12px 16px !important;
    backdrop-filter: blur(8px) !important;
    transition: all 0.3s ease !important;
}

textarea:focus, input[type="text"]:focus {
    border-color: rgba(155,127,212,0.5) !important;
    outline: none !important;
    box-shadow: 
        0 0 0 3px rgba(123,79,212,0.15),
        0 0 20px rgba(91,47,168,0.1) !important;
    background: rgba(20,12,42,0.8) !important;
}

textarea::placeholder { 
    color: rgba(155,127,212,0.4) !important;
    font-style: italic !important;
}

/* ── Buttons ───────────────────────────────────────────── */
button[aria-label="Submit"],
button.submit,
#component-submit-btn,
button[type="submit"],
.primary {
    background: linear-gradient(135deg, rgba(91,47,168,0.85), rgba(123,79,212,0.75)) !important;
    border: 1px solid rgba(155,127,212,0.35) !important;
    border-radius: 12px !important;
    color: #f0e8ff !important;
    font-weight: 500 !important;
    letter-spacing: 0.02em !important;
    padding: 10px 20px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 12px rgba(91,47,168,0.2) !important;
}

button[aria-label="Submit"]:hover,
.primary:hover {
    background: linear-gradient(135deg, rgba(123,79,212,0.95), rgba(155,127,212,0.85)) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(123,79,212,0.3) !important;
}

button[aria-label="Submit"]:active,
.primary:active {
    transform: translateY(0) !important;
}

/* Stop button */
.stop {
    background: rgba(180,60,60,0.6) !important;
    border: 1px solid rgba(220,100,100,0.3) !important;
    border-radius: 12px !important;
}

/* ── Examples ────────────────────────────────────────────── */
.examples {
    background: rgba(15,10,30,0.4) !important;
    border: 1px solid rgba(155,127,212,0.15) !important;
    border-radius: 14px !important;
    padding: 8px !important;
}

.example-item {
    background: rgba(91,47,168,0.15) !important;
    border: 1px solid rgba(155,127,212,0.2) !important;
    border-radius: 10px !important;
    color: #c4a8ff !important;
    font-size: 12px !important;
    padding: 6px 12px !important;
    transition: all 0.2s ease !important;
}

.example-item:hover {
    background: rgba(91,47,168,0.3) !important;
    border-color: rgba(155,127,212,0.4) !important;
    transform: translateX(2px) !important;
}

/* ── Typography ────────────────────────────────────────── */
.gradio-container h1, h2, h3 {
    color: #e8deff !important;
    font-family: 'Playfair Display', Georgia, serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.04em !important;
}

.gradio-container h1 {
    font-size: 1.8rem !important;
    background: linear-gradient(135deg, #e8deff, #c4a8ff) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    background-clip: text !important;
}

/* ── Scrollbars ────────────────────────────────────────── */
* { 
    scrollbar-width: thin; 
    scrollbar-color: rgba(123,79,212,0.5) rgba(15,10,30,0.3); 
}

::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { 
    background: rgba(15,10,30,0.3); 
    border-radius: 3px; 
}
::-webkit-scrollbar-thumb { 
    background: linear-gradient(180deg, rgba(123,79,212,0.5), rgba(91,47,168,0.4)); 
    border-radius: 3px; 
}
::-webkit-scrollbar-thumb:hover { 
    background: linear-gradient(180deg, rgba(155,127,212,0.6), rgba(123,79,212,0.5)); 
}

/* ── Glassmorphic panels ───────────────────────────────── */
.panel, .form, .block, .gap {
    background: rgba(15,10,30,0.3) !important;
    border: 1px solid rgba(155,127,212,0.12) !important;
    border-radius: 16px !important;
    backdrop-filter: blur(8px) !important;
}

/* ── Footer / info ───────────────────────────────────────── */
footer, .gradio-footer {
    display: none !important;
}

/* ── Responsive ────────────────────────────────────────── */
@media (max-width: 768px) {
    #aiko-main-row { flex-direction: column !important; }
    #aiko-chat-col, #aiko-vrm-col { 
        height: auto !important; 
        min-height: 50vh !important;
    }
    #aiko-vrm-col { min-height: 400px !important; }
    .gradio-container { padding: 12px !important; }
}
"""