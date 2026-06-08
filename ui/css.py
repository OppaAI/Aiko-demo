CSS = """
/* ═══════════════════════════════════════════════════════
   Aiko-chan — Professional Chat AI Interface
   ═══════════════════════════════════════════════════════ */

/* ── Reset & root variables ── */
:root {
    --ak-bg:           #0a0f1a;
    --ak-surface:      #111827;
    --ak-surface2:     #1a2235;
    --ak-surface3:     #212d45;
    --ak-border:       rgba(99, 140, 200, 0.10);
    --ak-border-focus: rgba(99, 160, 255, 0.35);
    --ak-accent:       #6c9fff;
    --ak-accent-dim:   rgba(108, 159, 255, 0.10);
    --ak-accent-glow:  rgba(108, 159, 255, 0.25);
    --ak-pink:         #d4a0ff;
    --ak-pink-dim:     rgba(212, 160, 255, 0.12);
    --ak-teal:         #5eead4;
    --ak-teal-dim:     rgba(94, 234, 212, 0.10);
    --ak-text:         #e2e8f0;
    --ak-text-muted:   rgba(226, 232, 240, 0.45);
    --ak-text-dim:     rgba(226, 232, 240, 0.65);
    --ak-user-bg:      linear-gradient(135deg, rgba(108,159,255,0.22), rgba(212,160,255,0.18));
    --ak-user-border:  rgba(140, 170, 255, 0.25);
    --ak-bot-bg:       rgba(30, 41, 59, 0.70);
    --ak-bot-border:   rgba(99, 140, 200, 0.12);
    --ak-radius:       16px;
    --ak-radius-sm:    10px;
    --ak-chat-height:  calc(100vh - 200px);
    --ak-shadow:       0 1px 3px rgba(0,0,0,0.30), 0 4px 16px rgba(0,0,0,0.15);
}

html, body {
    background: var(--ak-bg) !important;
    color: var(--ak-text) !important;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Hide all Gradio chrome ── */
footer,
.svelte-1ipelgc,
.gradio-container > .app > .wrap > .gap > .block > .label-wrap,
.block > .label-wrap,
.gradio-container .prose,
.chat-interface .disclaimer {
    display: none !important;
}

.app, .wrap, .gap, .form, .panel,
.block, [class*="gradio-"] > div {
    background: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

/* ── Main container ── */
.gradio-container {
    max-width: 1360px !important;
    min-height: 100vh !important;
    padding: 0 !important;
    background: var(--ak-bg) !important;
}

/* ══════════════════════════════════════════════════════
   HEADER
   ══════════════════════════════════════════════════════ */
#aiko-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 14px;
    padding: 18px 24px;
    background: rgba(17, 24, 39, 0.60) !important;
    backdrop-filter: blur(20px) saturate(1.2);
    -webkit-backdrop-filter: blur(20px) saturate(1.2);
    border-bottom: 1px solid var(--ak-border);
    position: sticky;
    top: 0;
    z-index: 100;
}

#aiko-header .header-avatar {
    width: 42px;
    height: 42px;
    border-radius: 50%;
    background: linear-gradient(135deg, var(--ak-accent), var(--ak-pink));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
    flex-shrink: 0;
    box-shadow: 0 0 20px var(--ak-accent-glow);
}

#aiko-header .header-text {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
}

#aiko-header h1 {
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: #fff !important;
    margin: 0 !important;
    letter-spacing: 0.02em !important;
    line-height: 1.3 !important;
}

#aiko-header .header-status {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.72rem !important;
    color: var(--ak-teal) !important;
    margin: 0 !important;
    letter-spacing: 0.03em !important;
}

#aiko-header .status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ak-teal);
    animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(94,234,212,0.5); }
    50%      { opacity: 0.7; box-shadow: 0 0 0 4px rgba(94,234,212,0); }
}

/* ══════════════════════════════════════════════════════
   CHAT INTERFACE WRAPPER
   ══════════════════════════════════════════════════════ */
.chat-interface {
    display: flex;
    flex-direction: column;
    height: var(--ak-chat-height) !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── Chatbot message area ── */
#aiko-chatbot {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    height: 100% !important;
    flex: 1 !important;
    overflow-y: auto !important;
    padding: 20px 16px !important;
}

#aiko-chatbot > div {
    background: transparent !important;
    border: none !important;
}

/* ── Message row wrappers ── */
#aiko-chatbot .message-row {
    padding: 4px 0 !important;
    background: transparent !important;
}

#aiko-chatbot .message-wrap {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
}

/* ══════════════════════════════════════════════════════
   MESSAGE BUBBLES
   ══════════════════════════════════════════════════════ */
#aiko-chatbot .message {
    padding: 12px 16px !important;
    border-radius: var(--ak-radius) !important;
    font-size: 0.9rem !important;
    line-height: 1.65 !important;
    max-width: 78% !important;
    word-wrap: break-word !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    position: relative !important;
    animation: msg-appear 0.35s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

@keyframes msg-appear {
    from { opacity: 0; transform: translateY(10px) scale(0.97); }
    to   { opacity: 1; transform: translateY(0) scale(1); }
}

/* ── User bubble ── */
#aiko-chatbot .message.user {
    background: var(--ak-user-bg) !important;
    border: 1px solid var(--ak-user-border) !important;
    border-radius: 20px 6px 20px 20px !important;
    color: #f0eeff !important;
    margin-left: auto !important;
    margin-right: 4px !important;
    backdrop-filter: blur(8px);
}

/* ── Bot bubble ── */
#aiko-chatbot .message.bot,
#aiko-chatbot .message.assistant {
    background: var(--ak-bot-bg) !important;
    border: 1px solid var(--ak-bot-border) !important;
    border-radius: 6px 20px 20px 20px !important;
    color: var(--ak-text) !important;
    margin-right: auto !important;
    margin-left: 4px !important;
    backdrop-filter: blur(8px);
}

/* ── Text color inside bubbles ── */
#aiko-chatbot .message.user *       { color: #f0eeff !important; }
#aiko-chatbot .message.bot *        { color: var(--ak-text) !important; }
#aiko-chatbot .message.assistant *  { color: var(--ak-text) !important; }

/* ── Bot message accent for search indicators ── */
#aiko-chatbot .message.bot em,
#aiko-chatbot .message.assistant em {
    color: var(--ak-accent) !important;
    font-style: italic !important;
    font-size: 0.82rem !important;
    display: block !important;
    margin-bottom: 6px !important;
    opacity: 0.80 !important;
}

/* ── Code blocks inside messages ── */
#aiko-chatbot .message pre {
    background: rgba(0,0,0,0.35) !important;
    border: 1px solid rgba(99,140,200,0.10) !important;
    border-radius: var(--ak-radius-sm) !important;
    padding: 12px !important;
    font-size: 0.82rem !important;
    overflow-x: auto !important;
    margin: 8px 0 !important;
}

#aiko-chatbot .message code {
    font-family: 'JetBrains Mono', 'Fira Code', 'SF Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ══════════════════════════════════════════════════════
   INPUT AREA
   ══════════════════════════════════════════════════════ */
.chat-interface .input-row {
    padding: 12px 16px 20px !important;
    background: rgba(17, 24, 39, 0.50) !important;
    backdrop-filter: blur(20px) saturate(1.2);
    -webkit-backdrop-filter: blur(20px) saturate(1.2);
    border-top: 1px solid var(--ak-border);
}

#aiko-input-wrap {
    display: flex;
    align-items: flex-end;
    gap: 10px;
    background: var(--ak-surface2) !important;
    border: 1px solid var(--ak-border) !important;
    border-radius: 28px !important;
    padding: 6px 6px 6px 18px !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}

#aiko-input-wrap:focus-within {
    border-color: var(--ak-border-focus) !important;
    box-shadow: 0 0 0 3px var(--ak-accent-dim), var(--ak-shadow) !important;
}

.gradio-container textarea {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    color: var(--ak-text) !important;
    caret-color: var(--ak-accent) !important;
    padding: 8px 0 !important;
    font-size: 0.9rem !important;
    resize: none !important;
    line-height: 1.5 !important;
    min-height: 24px !important;
    max-height: 120px !important;
    flex: 1 !important;
    outline: none !important;
    box-shadow: none !important;
}

.gradio-container textarea:focus {
    border-color: transparent !important;
    outline: none !important;
    box-shadow: none !important;
}

.gradio-container textarea::placeholder {
    color: var(--ak-text-muted) !important;
}

/* ── Send button ── */
#aiko-send-btn,
.chat-interface button[aria-label="Submit"],
.chat-interface button.submit-btn {
    background: linear-gradient(135deg, var(--ak-accent), #8b6fff) !important;
    border: none !important;
    border-radius: 50% !important;
    color: #fff !important;
    width: 40px !important;
    height: 40px !important;
    min-width: 40px !important;
    padding: 0 !important;
    flex-shrink: 0 !important;
    transition: transform 0.15s ease, box-shadow 0.25s ease, opacity 0.2s ease !important;
    box-shadow: 0 2px 10px rgba(108, 159, 255, 0.30) !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

#aiko-send-btn:hover,
.chat-interface button[aria-label="Submit"]:hover,
.chat-interface button.submit-btn:hover {
    transform: scale(1.08) !important;
    box-shadow: 0 4px 20px rgba(108, 159, 255, 0.45) !important;
}

#aiko-send-btn:active,
.chat-interface button[aria-label="Submit"]:active,
.chat-interface button.submit-btn:active {
    transform: scale(0.95) !important;
}

/* ── Secondary buttons (clear, etc.) ── */
.chat-interface .secondary-btn,
.chat-interface button:not([aria-label="Submit"]):not(.submit-btn):not(#aiko-send-btn) {
    background: var(--ak-surface2) !important;
    border: 1px solid var(--ak-border) !important;
    border-radius: 12px !important;
    color: var(--ak-text-dim) !important;
    font-size: 0.78rem !important;
    padding: 6px 14px !important;
    transition: background 0.2s ease, color 0.2s ease !important;
}

.chat-interface .secondary-btn:hover {
    background: var(--ak-surface3) !important;
    color: var(--ak-text) !important;
}

/* ══════════════════════════════════════════════════════
   SIDEBAR (VRM Viewer Column)
   ══════════════════════════════════════════════════════ */
#aiko-col {
    padding: 0 0 0 12px !important;
}

#aiko-sidebar {
    background: var(--ak-surface) !important;
    border: 1px solid var(--ak-border) !important;
    border-radius: var(--ak-radius) !important;
    padding: 16px !important;
    height: 100% !important;
    box-shadow: var(--ak-shadow) !important;
    overflow: hidden;
}

/* ══════════════════════════════════════════════════════
   STATUS & BADGE COMPONENTS
   ══════════════════════════════════════════════════════ */
.aiko-status {
    display: inline-flex !important;
    align-items: center !important;
    gap: 6px !important;
    font-size: 0.74rem !important;
    color: var(--ak-accent) !important;
    background: var(--ak-accent-dim) !important;
    border: 1px solid rgba(108,159,255,0.18) !important;
    border-radius: 20px !important;
    padding: 3px 10px !important;
    margin-bottom: 8px !important;
    letter-spacing: 0.02em !important;
}

.aiko-mem-badge {
    background: var(--ak-pink-dim) !important;
    border: 1px solid rgba(212,160,255,0.18) !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
    font-size: 0.78rem !important;
    color: var(--ak-pink) !important;
    margin-bottom: 8px !important;
}

/* ══════════════════════════════════════════════════════
   TYPING INDICATOR
   ══════════════════════════════════════════════════════ */
.typing-indicator {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 0;
}

.typing-indicator span {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: var(--ak-accent);
    opacity: 0.4;
    animation: typing-bounce 1.4s ease-in-out infinite;
}

.typing-indicator span:nth-child(2) { animation-delay: 0.15s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.30s; }

@keyframes typing-bounce {
    0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
    30%           { transform: translateY(-6px); opacity: 1; }
}

/* ══════════════════════════════════════════════════════
   SCROLLBAR
   ══════════════════════════════════════════════════════ */
* {
    scrollbar-width: thin;
    scrollbar-color: rgba(108,159,255,0.20) transparent;
}

::-webkit-scrollbar       { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(108,159,255,0.20);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(108,159,255,0.35);
}

/* ══════════════════════════════════════════════════════
   MISC
   ══════════════════════════════════════════════════════ */
.gradio-container p,
.gradio-container label,
.gradio-container span {
    color: var(--ak-text) !important;
}

.gradio-container .row { gap: 0 !important; }

/* ── Welcome screen ── */
.aiko-welcome {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    padding: 60px 20px;
    text-align: center;
}

.aiko-welcome .welcome-icon {
    font-size: 2.8rem;
    margin-bottom: 4px;
}

.aiko-welcome h2 {
    font-size: 1.3rem !important;
    font-weight: 600 !important;
    color: #fff !important;
    margin: 0 !important;
}

.aiko-welcome p {
    font-size: 0.85rem !important;
    color: var(--ak-text-muted) !important;
    max-width: 400px;
    line-height: 1.6;
}

.aiko-welcome .suggestion-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    justify-content: center;
    margin-top: 8px;
}

.aiko-welcome .chip {
    background: var(--ak-surface2);
    border: 1px solid var(--ak-border);
    border-radius: 20px;
    padding: 8px 16px;
    font-size: 0.8rem;
    color: var(--ak-text-dim);
    cursor: pointer;
    transition: all 0.2s ease;
}

.aiko-welcome .chip:hover {
    background: var(--ak-surface3);
    border-color: var(--ak-border-focus);
    color: var(--ak-accent);
}

/* ── Responsive ── */
@media (max-width: 768px) {
    .gradio-container { max-width: 100vw !important; }
    #aiko-chatbot .message { max-width: 88% !important; }
    #aiko-header h1 { font-size: 1rem !important; }
}

/* ── Selection color ── */
::selection {
    background: rgba(108,159,255,0.30);
    color: #fff;
}

/* ── Date separator ── */
.aiko-date-sep {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 16px 0;
    font-size: 0.72rem;
    color: var(--ak-text-muted);
    letter-spacing: 0.04em;
}
.aiko-date-sep::before,
.aiko-date-sep::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--ak-border);
}
"""