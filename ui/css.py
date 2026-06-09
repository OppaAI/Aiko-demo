CSS = """
/* ── Keyframes ── */
@keyframes orb-pulse {
    0%, 100% { box-shadow: 0 0 28px rgba(80,150,255,0.35), 0 0 8px rgba(80,150,255,0.2); }
    50%       { box-shadow: 0 0 44px rgba(80,150,255,0.55), 0 0 16px rgba(80,150,255,0.35); }
}
@keyframes orb-ring {
    0%   { transform: scale(1);   opacity: 0.35; }
    50%  { transform: scale(1.08); opacity: 0.15; }
    100% { transform: scale(1);   opacity: 0.35; }
}
@keyframes dot-bounce {
    0%, 80%, 100% { transform: translateY(0);    opacity: 0.4; }
    40%           { transform: translateY(-6px); opacity: 1;   }
}

/* ── Root vars ── */
:root {
    --ak-bg:          #070d1a;
    --ak-surface:     #0d1527;
    --ak-surface2:    #111d35;
    --ak-border:      rgba(80,140,255,0.14);
    --ak-border2:     rgba(80,140,255,0.22);
    --ak-blue:        #4a8fff;
    --ak-blue-dim:    rgba(74,143,255,0.12);
    --ak-text:        #dde8ff;
    --ak-text-muted:  rgba(180,200,255,0.45);
    --ak-user-bg:     rgba(60,90,220,0.28);
    --ak-user-border: rgba(100,140,255,0.30);
    --ak-bot-bg:      rgba(255,255,255,0.04);
    --ak-bot-border:  rgba(80,140,255,0.14);
    --ak-radius:      16px;
}

/* ── Global reset ── */
html, body, .gradio-container {
    background: var(--ak-bg) !important;
    color: var(--ak-text) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* ── Hide Gradio chrome ── */
footer,
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

/* ── Orb section ── */
#aiko-orb-section {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 32px 0 20px;
    gap: 0;
}

#aiko-orb-wrap {
    position: relative;
    width: 110px;
    height: 110px;
    display: flex;
    align-items: center;
    justify-content: center;
}

#aiko-orb-ring-outer {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 1px solid rgba(80,140,255,0.18);
    animation: orb-ring 3.5s ease-in-out infinite;
}

#aiko-orb-ring-inner {
    position: absolute;
    inset: 14px;
    border-radius: 50%;
    border: 1px solid rgba(80,140,255,0.28);
    animation: orb-ring 3.5s ease-in-out infinite 0.5s;
}

#aiko-orb {
    width: 66px;
    height: 66px;
    border-radius: 50%;
    background: radial-gradient(circle at 38% 34%, #60b0ff, #2060d0 52%, #0a1550);
    animation: orb-pulse 3s ease-in-out infinite;
    position: relative;
    z-index: 1;
}

#aiko-orb::after {
    content: '';
    position: absolute;
    top: 13px;
    left: 17px;
    width: 16px;
    height: 9px;
    background: rgba(255,255,255,0.26);
    border-radius: 50%;
    transform: rotate(-30deg);
}

#aiko-greeting {
    text-align: center;
    margin-top: 16px;
}

#aiko-greeting h2 {
    font-size: 1.15rem !important;
    font-weight: 500 !important;
    color: rgba(220,235,255,0.92) !important;
    margin: 0 0 5px !important;
    letter-spacing: 0.01em !important;
}

#aiko-greeting p {
    font-size: 0.75rem !important;
    color: var(--ak-text-muted) !important;
    margin: 0 !important;
    letter-spacing: 0.05em !important;
    text-transform: uppercase !important;
}

/* ── Suggestion pills ── */
#aiko-suggestions {
    display: flex;
    gap: 7px;
    justify-content: center;
    flex-wrap: wrap;
    padding: 14px 16px 8px;
}

.aiko-pill {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(80,140,255,0.20) !important;
    border-radius: 20px !important;
    padding: 5px 14px !important;
    font-size: 0.76rem !important;
    color: rgba(160,195,255,0.75) !important;
    cursor: pointer !important;
    transition: background 0.2s, border-color 0.2s !important;
    white-space: nowrap !important;
}
.aiko-pill:hover {
    background: rgba(80,140,255,0.12) !important;
    border-color: rgba(80,140,255,0.40) !important;
    color: rgba(190,215,255,0.9) !important;
}

/* ── Chatbot container ── */
#aiko-chatbot {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

#aiko-chatbot > div {
    background: transparent !important;
    border: none !important;
    padding: 0 8px !important;
}

/* ── Scrollable message area ── */
#aiko-chatbot .message-wrap {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
}

/* ── Message rows ── */
#aiko-chatbot .message-row {
    gap: 8px !important;
    padding: 2px 4px !important;
}

/* ── Individual message bubbles ── */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="bot"] {
    font-size: 0.875rem !important;
    line-height: 1.6 !important;
    border-radius: var(--ak-radius) !important;
    padding: 10px 14px !important;
    max-width: 78% !important;
    word-break: break-word !important;
    border: 1px solid transparent !important;
    box-shadow: none !important;
}

/* User bubble */
#aiko-chatbot [data-testid="user"] {
    background: var(--ak-user-bg) !important;
    border-color: var(--ak-user-border) !important;
    border-radius: 16px 4px 16px 16px !important;
    color: rgba(210,225,255,0.92) !important;
    margin-left: auto !important;
    margin-right: 6px !important;
}

/* Bot bubble */
#aiko-chatbot [data-testid="bot"] {
    background: var(--ak-bot-bg) !important;
    border-color: var(--ak-bot-border) !important;
    border-radius: 4px 16px 16px 16px !important;
    color: rgba(210,225,255,0.82) !important;
    margin-right: auto !important;
    margin-left: 6px !important;
}

/* Force text color inside bubbles */
#aiko-chatbot [data-testid="user"]  * { color: rgba(210,225,255,0.92) !important; }
#aiko-chatbot [data-testid="bot"]   * { color: rgba(210,225,255,0.82) !important; }

/* ── message-row alignment ── */
#aiko-chatbot .message-row.user-row {
    justify-content: flex-end !important;
}
#aiko-chatbot .message-row.bot-row {
    justify-content: flex-start !important;
}

/* ── Italic search status inside bot bubble ── */
#aiko-chatbot [data-testid="bot"] em {
    color: var(--ak-blue) !important;
    font-style: italic !important;
    font-size: 0.80rem !important;
    display: block !important;
    margin-bottom: 6px !important;
    opacity: 0.85 !important;
}

/* ── Loading dots ── */
#aiko-chatbot .dots {
    display: flex !important;
    gap: 4px !important;
    padding: 4px 2px !important;
}
#aiko-chatbot .dot {
    width: 6px !important;
    height: 6px !important;
    border-radius: 50% !important;
    background: rgba(100,160,255,0.6) !important;
    animation: dot-bounce 1.3s ease-in-out infinite !important;
}
#aiko-chatbot .dot:nth-child(2) { animation-delay: 0.16s !important; }
#aiko-chatbot .dot:nth-child(3) { animation-delay: 0.32s !important; }

/* ── Avatar containers — hide by default (no avatars set) ── */
#aiko-chatbot .avatar-container { display: none !important; }

/* ── Input area outer wrapper ── */
.gradio-container .block:has(textarea[data-testid="textbox"]) {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 0 !important;
}

/* ── Input row ── */
.gradio-container .input-row {
    background: var(--ak-surface2) !important;
    border: 1px solid var(--ak-border2) !important;
    border-radius: 28px !important;
    padding: 6px 8px 6px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    transition: border-color 0.2s !important;
}
.gradio-container .input-row:focus-within {
    border-color: rgba(80,140,255,0.45) !important;
    box-shadow: 0 0 0 3px rgba(74,143,255,0.08) !important;
}

/* ── Textarea inside input-row ── */
.gradio-container textarea[data-testid="textbox"] {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    color: var(--ak-text) !important;
    caret-color: var(--ak-blue) !important;
    font-size: 0.875rem !important;
    line-height: 1.5 !important;
    resize: none !important;
    padding: 4px 0 !important;
    flex: 1 !important;
}
.gradio-container textarea[data-testid="textbox"]::placeholder {
    color: var(--ak-text-muted) !important;
}

/* ── Submit button (icon button inside textbox) ── */
.gradio-container .textarea-wrapper button[aria-label],
.gradio-container [data-testid="submit-btn"],
.gradio-container button.submit-btn,
.gradio-container .input-row > button {
    background: rgba(74,143,255,0.18) !important;
    border: 1px solid rgba(74,143,255,0.35) !important;
    border-radius: 50% !important;
    color: rgba(160,200,255,0.9) !important;
    width: 34px !important;
    height: 34px !important;
    min-width: 34px !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex-shrink: 0 !important;
    transition: background 0.2s !important;
}
.gradio-container .textarea-wrapper button[aria-label]:hover,
.gradio-container .input-row > button:hover {
    background: rgba(74,143,255,0.30) !important;
}

/* ── Sidebar ── */
#aiko-col {
    padding: 0 0 0 12px !important;
}

/* ── Status pill ── */
.aiko-status {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    font-size: 0.74rem !important;
    color: var(--ak-blue) !important;
    background: var(--ak-blue-dim) !important;
    border: 1px solid rgba(74,143,255,0.22) !important;
    border-radius: 20px !important;
    padding: 3px 10px !important;
    margin-bottom: 8px !important;
    letter-spacing: 0.02em !important;
}

/* ── Date divider ── */
.aiko-date-divider {
    text-align: center !important;
    font-size: 0.70rem !important;
    color: var(--ak-text-muted) !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
    margin: 8px 0 6px !important;
    position: relative !important;
}
.aiko-date-divider::before,
.aiko-date-divider::after {
    content: '' !important;
    position: absolute !important;
    top: 50% !important;
    width: 30% !important;
    height: 1px !important;
    background: var(--ak-border) !important;
}
.aiko-date-divider::before { left: 0; }
.aiko-date-divider::after  { right: 0; }

/* ── Scrollbars ── */
* { scrollbar-width: thin; scrollbar-color: rgba(74,143,255,0.25) transparent; }
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(74,143,255,0.25); border-radius: 2px; }

/* ── General text ── */
.gradio-container p,
.gradio-container label,
.gradio-container span { color: var(--ak-text) !important; }

/* ── Layout row gap ── */
.gradio-container .row { gap: 12px !important; }

/* ── Placeholder empty state ── */
#aiko-chatbot .placeholder {
    display: none !important;
}
"""