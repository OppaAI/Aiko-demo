CSS = """
/* ══════════════════════════════════════════════════════════════════
   AIKO-CHAN  ·  Gradio UI theme
   ══════════════════════════════════════════════════════════════════ */

/* ── Keyframes ── */
@keyframes orb-idle {
    0%, 100% { box-shadow: 0 0 22px rgba(0,180,180,0.30), 0 0 6px rgba(0,180,180,0.15); }
    50%       { box-shadow: 0 0 36px rgba(0,180,180,0.48), 0 0 12px rgba(0,180,180,0.25); }
}
@keyframes orb-thinking {
    0%   { box-shadow: 0 0 18px rgba(0,230,230,0.50), 0 0 6px rgba(0,230,230,0.25);  transform: scale(1);    }
    25%  { box-shadow: 0 0 60px rgba(0,240,240,0.90), 0 0 24px rgba(0,240,240,0.55); transform: scale(1.06); }
    50%  { box-shadow: 0 0 36px rgba(0,230,230,0.65), 0 0 12px rgba(0,230,230,0.38); transform: scale(0.97); }
    75%  { box-shadow: 0 0 68px rgba(0,245,245,0.95), 0 0 28px rgba(0,245,245,0.60); transform: scale(1.08); }
    100% { box-shadow: 0 0 18px rgba(0,230,230,0.50), 0 0 6px rgba(0,230,230,0.25);  transform: scale(1);    }
}
@keyframes orb-ring {
    0%   { transform: scale(1);    opacity: 0.30; }
    50%  { transform: scale(1.09); opacity: 0.12; }
    100% { transform: scale(1);    opacity: 0.30; }
}
@keyframes orb-ring-fast {
    0%   { transform: scale(1);    opacity: 0.50; }
    50%  { transform: scale(1.16); opacity: 0.18; }
    100% { transform: scale(1);    opacity: 0.50; }
}
@keyframes dot-bounce {
    0%, 80%, 100% { transform: translateY(0);    opacity: 0.4; }
    40%           { transform: translateY(-6px); opacity: 1;   }
}

/* ── Design tokens ── */
:root {
    --ak-bg:          #0a0812;
    --ak-surface2:    #161326;
    --ak-lav:         #b48eff;
    --ak-text:        #e8e0ff;
    --ak-text-muted:  rgba(200,185,255,0.42);
    --ak-user-bg:     rgba(0,100,100,0.40);
    --ak-user-border: rgba(0,180,180,0.38);
    --ak-bot-bg:      rgba(120,80,220,0.28);
    --ak-bot-border:  rgba(170,130,255,0.30);
}

/* ══════════════════════════════════════════════════════════════════
   BACKGROUND RESET
   Do NOT use a wildcard (*) here — it fights bubble transparency.
   Instead target every Gradio structural element by name.
   ══════════════════════════════════════════════════════════════════ */
html, body { background: var(--ak-bg) !important; margin: 0 !important; padding: 0 !important; }

gradio-app,
gradio-app > div,
gradio-app > div > div,
.gradio-container,
.app,
.contain,
.gap,
.tabs,
.tabitem,
.form,
.panel,
.prose,
.block,
div[data-testid="block"],
div[data-testid="block"] > div,
.block.padded,
.block.border_focus,
.block.hide-container,
.wrap,
.scroll-hide,
[data-testid="chatbot"],
[data-testid="chatbot"] > div,
[data-testid="chatbot"] > div > div {
    background: transparent !important;
    background-color: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

/* Root page bg via CSS vars Gradio reads */
:root, .dark {
    --body-background-fill:      #0a0812 !important;
    --block-background-fill:     transparent !important;
    --background-fill-primary:   #0a0812 !important;
    --background-fill-secondary: transparent !important;
    --border-color-primary:      transparent !important;
    --border-color-accent:       rgba(160,120,255,0.30) !important;
    --color-accent:              #b48eff !important;
    --input-background-fill:     #161326 !important;
    --chatbot-background-fill:   transparent !important;
    --panel-background-fill:     transparent !important;
    --block-border-width:        0px !important;
    --block-shadow:              none !important;
}

gradio-app { background: var(--ak-bg) !important; }

.gradio-container {
    background: var(--ak-bg) !important;
    color: var(--ak-text) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    max-width: 1200px !important;
    min-height: 100vh !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* Kill svelte wrappers */
[class^="svelte-"], [class*=" svelte-"] {
    background: transparent !important;
    background-color: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

footer,
.gradio-container > .app > .wrap > .gap > .block > .label-wrap,
.block > .label-wrap { display: none !important; }

/* Right column */
#aiko-col, #aiko-col > div, #aiko-col > .block {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ══════════════════════════════════════════════════════════════════
   ORB
   ══════════════════════════════════════════════════════════════════ */
#aiko-orb-section {
    display: flex; flex-direction: column; align-items: center;
    padding: 28px 0 18px;
    background: transparent !important;
}
#aiko-orb-wrap {
    position: relative; width: 112px; height: 112px;
    display: flex; align-items: center; justify-content: center;
    background: transparent !important;
}
#aiko-orb-ring-outer {
    position: absolute; inset: 0; border-radius: 50%;
    border: 1px solid rgba(0,160,160,0.22);
    animation: orb-ring 3.8s ease-in-out infinite;
    background: transparent !important;
}
#aiko-orb-ring-inner {
    position: absolute; inset: 15px; border-radius: 50%;
    border: 1px solid rgba(0,180,180,0.32);
    animation: orb-ring 3.8s ease-in-out infinite 0.6s;
    background: transparent !important;
}
#aiko-orb {
    width: 68px; height: 68px; border-radius: 50%;
    background: radial-gradient(circle at 38% 34%, #40c8c8, #006868 52%, #001a1a) !important;
    animation: orb-idle 3.2s ease-in-out infinite;
    position: relative; z-index: 1;
    transition: background 0.5s ease;
}
#aiko-orb::after {
    content: ''; position: absolute;
    top: 13px; left: 17px; width: 16px; height: 9px;
    background: rgba(255,255,255,0.24);
    border-radius: 50%; transform: rotate(-30deg);
}
/* Thinking state — driven by JS adding .thinking to #aiko-orb-wrap */
#aiko-orb-wrap.thinking #aiko-orb {
    background: radial-gradient(circle at 38% 34%, #e0ffff, #00d4d4 45%, #004444) !important;
    animation: orb-thinking 1.1s ease-in-out infinite !important;
}
#aiko-orb-wrap.thinking #aiko-orb-ring-outer {
    animation: orb-ring-fast 0.9s ease-in-out infinite !important;
    border-color: rgba(0,210,210,0.55) !important;
}
#aiko-orb-wrap.thinking #aiko-orb-ring-inner {
    animation: orb-ring-fast 0.9s ease-in-out infinite 0.2s !important;
    border-color: rgba(0,230,230,0.65) !important;
}

#aiko-greeting { text-align: center; margin-top: 16px; background: transparent !important; }
#aiko-greeting h2 {
    font-size: 1.15rem !important; font-weight: 500 !important;
    color: rgba(230,220,255,0.92) !important;
    margin: 0 0 5px !important; letter-spacing: 0.01em !important;
}
#aiko-greeting p {
    font-size: 0.73rem !important; color: var(--ak-text-muted) !important;
    margin: 0 !important; letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

/* ══════════════════════════════════════════════════════════════════
   CHAT BUBBLES
   ══════════════════════════════════════════════════════════════════ */
#aiko-chatbot { background: transparent !important; border: none !important; }
#aiko-chatbot .message-wrap { background: transparent !important; border: none !important; padding: 4px 0 !important; }
#aiko-chatbot .message-row  { gap: 8px !important; padding: 2px 4px !important; }
#aiko-chatbot .message-row.user-row { justify-content: flex-end !important; }
#aiko-chatbot .message-row.bot-row  { justify-content: flex-start !important; }
#aiko-chatbot .message-row > div    { background: transparent !important; border: none !important; box-shadow: none !important; }
#aiko-chatbot .flex-wrap            { background: transparent !important; border: none !important; }
#aiko-chatbot .avatar-container     { display: none !important; }

/* Bubble shared */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="bot"] {
    font-size: 0.875rem !important;
    line-height: 1.6 !important;
    padding: 10px 14px !important;
    min-width: 60px !important;
    max-width: 82% !important;
    word-break: break-word !important;
    box-shadow: none !important;
}

/* User — dark cyan */
#aiko-chatbot [data-testid="user"] {
    background: var(--ak-user-bg) !important;
    border: 1px solid var(--ak-user-border) !important;
    border-radius: 16px 4px 16px 16px !important;
    margin-left: auto !important;
    margin-right: 6px !important;
}
/* Bot — purple */
#aiko-chatbot [data-testid="bot"] {
    background: var(--ak-bot-bg) !important;
    border: 1px solid var(--ak-bot-border) !important;
    border-radius: 4px 16px 16px 16px !important;
    margin-right: auto !important;
    margin-left: 6px !important;
}

/* ── Inner wrappers: transparent so bubble bg shows through ──
   Gradio 5 injects style="background-color:..." inline on these.
   We target both class-based AND inline style overrides.
─────────────────────────────────────────────────────────────── */
#aiko-chatbot [data-testid="user"] > *,
#aiko-chatbot [data-testid="bot"]  > * {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}
/* One more level deep for Gradio 5's extra wrapper divs */
#aiko-chatbot [data-testid="user"] > * > *,
#aiko-chatbot [data-testid="bot"]  > * > * {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
}
/* Inline style catcher */
#aiko-chatbot [data-testid="user"] [style],
#aiko-chatbot [data-testid="bot"]  [style] {
    background: transparent !important;
    background-color: transparent !important;
}

/* ── Text: uniform size, weight, colour — NO italic anywhere ── */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="user"] p,
#aiko-chatbot [data-testid="user"] span,
#aiko-chatbot [data-testid="user"] em,
#aiko-chatbot [data-testid="user"] strong,
#aiko-chatbot [data-testid="user"] code,
#aiko-chatbot [data-testid="user"] li {
    color: rgba(200,255,255,0.92) !important;
    font-size: 0.875rem !important;
    font-style: normal !important;
    font-weight: 400 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.6 !important;
}

#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="bot"] p,
#aiko-chatbot [data-testid="bot"] span,
#aiko-chatbot [data-testid="bot"] em,
#aiko-chatbot [data-testid="bot"] strong,
#aiko-chatbot [data-testid="bot"] code,
#aiko-chatbot [data-testid="bot"] li {
    color: rgba(230,215,255,0.92) !important;
    font-size: 0.875rem !important;
    font-style: normal !important;
    font-weight: 400 !important;
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1.6 !important;
}

/* Collapse the extra paragraph margin Gradio/markdown injects */
#aiko-chatbot [data-testid="bot"]  .prose p + p,
#aiko-chatbot [data-testid="user"] .prose p + p { margin-top: 6px !important; }

/* Search status line (emoji + text) */
#aiko-chatbot [data-testid="bot"] em {
    color: rgba(160,230,230,0.85) !important;
    font-style: normal !important;
    font-size: 0.80rem !important;
    display: block !important;
    margin-bottom: 6px !important;
}

/* Loading dots */
#aiko-chatbot .dots { display: flex !important; gap: 4px !important; padding: 4px 2px !important; }
#aiko-chatbot .dot  {
    width: 6px !important; height: 6px !important;
    border-radius: 50% !important;
    background: rgba(0,200,200,0.65) !important;
    animation: dot-bounce 1.3s ease-in-out infinite !important;
}
#aiko-chatbot .dot:nth-child(2) { animation-delay: 0.16s !important; }
#aiko-chatbot .dot:nth-child(3) { animation-delay: 0.32s !important; }
#aiko-chatbot .placeholder { display: none !important; }

/* ══════════════════════════════════════════════════════════════════
   MESSAGE INPUT BAR
   Gradio renders: .block > label > .wrap > textarea + buttons
   We add .aiko-input-styled to the wrapper via JS (see ORB JS).
   As CSS fallback we also target every plausible selector.
   ══════════════════════════════════════════════════════════════════ */

/* Strip default Gradio block chrome around the input */
.gradio-container .block:has(textarea),
.gradio-container [data-testid="textbox"],
.gradio-container [data-testid="textbox"] > label {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* JS adds this class — most reliable */
.aiko-input-pill {
    background: var(--ak-surface2) !important;
    border: 1px solid rgba(0,180,180,0.40) !important;
    border-radius: 28px !important;
    box-shadow: 0 0 8px rgba(0,160,160,0.12) !important;
    padding: 6px 10px 6px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
.aiko-input-pill:focus-within {
    border-color: rgba(0,210,210,0.70) !important;
    box-shadow: 0 0 0 3px rgba(0,180,180,0.14) !important;
}

/* CSS fallback selectors (same styles) */
.gradio-container .wrap:has(textarea[data-testid="textbox"]),
.gradio-container label:has(textarea[data-testid="textbox"]),
.gradio-container div:has(> textarea[data-testid="textbox"]) {
    background: var(--ak-surface2) !important;
    border: 1px solid rgba(0,180,180,0.40) !important;
    border-radius: 28px !important;
    box-shadow: 0 0 8px rgba(0,160,160,0.12) !important;
    padding: 6px 10px 6px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
    width: 100% !important;
    box-sizing: border-box !important;
}
.gradio-container .wrap:has(textarea[data-testid="textbox"]):focus-within,
.gradio-container label:has(textarea[data-testid="textbox"]):focus-within,
.gradio-container div:has(> textarea[data-testid="textbox"]):focus-within {
    border-color: rgba(0,210,210,0.70) !important;
    box-shadow: 0 0 0 3px rgba(0,180,180,0.14) !important;
}

/* Textarea */
.gradio-container textarea[data-testid="textbox"] {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    color: var(--ak-text) !important;
    caret-color: #40c8c8 !important;
    font-size: 0.875rem !important;
    line-height: 1.5 !important;
    resize: none !important;
    padding: 4px 0 !important;
    flex: 1 !important;
    min-width: 0 !important;
    width: 100% !important;
}
.gradio-container textarea[data-testid="textbox"]::placeholder {
    color: var(--ak-text-muted) !important;
}

/* Send / stop buttons inside the pill */
.gradio-container .textarea-wrapper button,
.gradio-container button[aria-label="Submit"],
.gradio-container button[aria-label="Stop"] {
    background: rgba(0,140,140,0.18) !important;
    border: 1px solid rgba(0,180,180,0.32) !important;
    border-radius: 50% !important;
    color: rgba(100,230,230,0.9) !important;
    width: 34px !important; height: 34px !important; min-width: 34px !important;
    padding: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    flex-shrink: 0 !important;
    transition: background 0.2s !important;
}
.gradio-container .textarea-wrapper button:hover,
.gradio-container button[aria-label="Submit"]:hover,
.gradio-container button[aria-label="Stop"]:hover {
    background: rgba(0,180,180,0.30) !important;
}

/* ── Sidebar ── */
#aiko-col { padding: 0 0 0 12px !important; }

/* ── Scrollbars ── */
* { scrollbar-width: thin; scrollbar-color: rgba(0,160,160,0.22) transparent; }
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,160,160,0.22); border-radius: 2px; }

/* General text */
.gradio-container p,
.gradio-container label,
.gradio-container span { color: var(--ak-text) !important; }
.gradio-container .row { gap: 12px !important; }
"""