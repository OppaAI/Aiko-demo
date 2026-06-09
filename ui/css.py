CSS = """
/* ══════════════════════════════════════════════════════════════════
   AIKO-CHAN  ·  Gradio UI theme
   ══════════════════════════════════════════════════════════════════ */

/* ── Keyframes ── */
@keyframes orb-idle {
    0%, 100% {
        box-shadow: 0 0 22px rgba(0,180,180,0.30), 0 0 6px rgba(0,180,180,0.15);
    }
    50% {
        box-shadow: 0 0 36px rgba(0,180,180,0.48), 0 0 12px rgba(0,180,180,0.25);
    }
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

/* ── Root vars ── */
:root {
    --ak-bg:          #0a0812;
    --ak-surface:     #100e1c;
    --ak-surface2:    #161326;
    --ak-border:      rgba(160,120,255,0.14);
    --ak-border2:     rgba(160,120,255,0.24);
    --ak-lav:         #b48eff;
    --ak-lav-dim:     rgba(160,120,255,0.12);
    --ak-lav-glow:    rgba(160,120,255,0.30);
    --ak-text:        #e8e0ff;
    --ak-text-muted:  rgba(200,185,255,0.42);

    /* ── Swapped bubble colours ──────────────────────────────────────
       User  → dark cyan  (was purple)
       Bot   → purple     (was near-white/transparent)
    ───────────────────────────────────────────────────────────────── */
    --ak-user-bg:     rgba(0,100,100,0.38);
    --ak-user-border: rgba(0,180,180,0.35);
    --ak-bot-bg:      rgba(120,80,220,0.26);
    --ak-bot-border:  rgba(170,130,255,0.28);

    --ak-radius:      16px;
}

/* ── Nuclear dark override ── */
html,
body,
gradio-app,
gradio-app > div,
gradio-app > div > div,
.gradio-container,
.gradio-container * {
    background-color: var(--ak-bg) !important;
}

/* Override Gradio theme CSS variables */
:root, .dark {
    --body-background-fill:          #0a0812 !important;
    --block-background-fill:         #0a0812 !important;
    --background-fill-primary:       #0a0812 !important;
    --background-fill-secondary:     #100e1c !important;
    --border-color-primary:          rgba(160,120,255,0.14) !important;
    --border-color-accent:           rgba(160,120,255,0.30) !important;
    --color-accent:                  #b48eff !important;
    --input-background-fill:         #161326 !important;
    --chatbot-background-fill:       #0a0812 !important;
}

gradio-app {
    background: var(--ak-bg) !important;
    --body-background-fill: var(--ak-bg) !important;
}

/* ── Global reset ── */
html, body, .gradio-container {
    background: var(--ak-bg) !important;
    color: var(--ak-text) !important;
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    margin: 0 !important;
    padding: 0 !important;
}

footer { display: none !important; }

.gradio-container > .app > .wrap > .gap > .block > .label-wrap,
.block > .label-wrap { display: none !important; }

/* Blanket dark override for ALL block/panel/wrap divs */
.app, .wrap, .gap, .form, .panel, .block,
[class*="gradio-"] > div,
div[data-testid="block"] {
    background: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

/* Kill Gradio 5 block wrappers */
div[data-testid="block"],
div[data-testid="block"] > div,
.block.padded,
.block.border_focus,
.block.hide-container,
.form {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
}

/* Nuke Gradio 5 svelte-generated wrapper panels */
[class^="svelte-"], [class*=" svelte-"] {
    background: transparent !important;
    border-color: transparent !important;
    box-shadow: none !important;
}

/* Kill the white chatbot panel */
#aiko-chatbot,
#aiko-chatbot > div,
#aiko-chatbot > div > div,
.gradio-container div[data-testid="chatbot"],
.gradio-container div[data-testid="chatbot"] > div {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Kill white user-message outer container */
#aiko-chatbot .message-row > div,
#aiko-chatbot .flex-wrap {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Right-column white panel (VRM viewer side) */
#aiko-col,
#aiko-col > div,
#aiko-col > .block {
    background: transparent !important;
    border: none !important;
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
    padding: 28px 0 18px;
}

#aiko-orb-wrap {
    position: relative;
    width: 112px;
    height: 112px;
    display: flex;
    align-items: center;
    justify-content: center;
}

#aiko-orb-ring-outer {
    position: absolute;
    inset: 0;
    border-radius: 50%;
    border: 1px solid rgba(0,160,160,0.22);
    animation: orb-ring 3.8s ease-in-out infinite;
}
#aiko-orb-ring-inner {
    position: absolute;
    inset: 15px;
    border-radius: 50%;
    border: 1px solid rgba(0,180,180,0.32);
    animation: orb-ring 3.8s ease-in-out infinite 0.6s;
}

/* ── Orb: dark cyan idle ── */
#aiko-orb {
    width: 68px;
    height: 68px;
    border-radius: 50%;
    /* Dark teal/cyan — deep at centre, dark at edge */
    background: radial-gradient(circle at 38% 34%, #40c8c8, #006868 52%, #001a1a);
    animation: orb-idle 3.2s ease-in-out infinite;
    position: relative;
    z-index: 1;
    transition: background 0.4s ease;
}
#aiko-orb::after {
    content: '';
    position: absolute;
    top: 13px; left: 17px;
    width: 16px; height: 9px;
    background: rgba(255,255,255,0.24);
    border-radius: 50%;
    transform: rotate(-30deg);
}

/* ── Orb: light cyan glowing thinking ── */
#aiko-orb-wrap.thinking #aiko-orb {
    /* Bright cyan core → pale at edges — clearly "lit up" */
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

#aiko-greeting {
    text-align: center;
    margin-top: 16px;
}
#aiko-greeting h2 {
    font-size: 1.15rem !important;
    font-weight: 500 !important;
    color: rgba(230,220,255,0.92) !important;
    margin: 0 0 5px !important;
    letter-spacing: 0.01em !important;
}
#aiko-greeting p {
    font-size: 0.73rem !important;
    color: var(--ak-text-muted) !important;
    margin: 0 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

/* ── Chatbot message area ── */
#aiko-chatbot .message-wrap {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
}
#aiko-chatbot .message-row {
    gap: 8px !important;
    padding: 2px 4px !important;
}
#aiko-chatbot .message-row.user-row { justify-content: flex-end !important; }
#aiko-chatbot .message-row.bot-row  { justify-content: flex-start !important; }

/* ── Bubbles ── */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="bot"] {
    font-size: 0.875rem !important;
    line-height: 1.6 !important;
    padding: 10px 14px !important;
    max-width: 78% !important;
    word-break: break-word !important;
    box-shadow: none !important;
}

/* User bubble — dark cyan */
#aiko-chatbot [data-testid="user"] {
    background: var(--ak-user-bg) !important;
    border: 1px solid var(--ak-user-border) !important;
    border-radius: 16px 4px 16px 16px !important;
    color: rgba(200,255,255,0.92) !important;
    margin-left: auto !important;
    margin-right: 6px !important;
}

/* Bot bubble — purple (was user's colour) */
#aiko-chatbot [data-testid="bot"] {
    background: var(--ak-bot-bg) !important;
    border: 1px solid var(--ak-bot-border) !important;
    border-radius: 4px 16px 16px 16px !important;
    color: rgba(230,215,255,0.92) !important;
    margin-right: auto !important;
    margin-left: 6px !important;
}

/* ── Transparent inner wrappers — bubble colour shows through ──
   Every Gradio 5 inner div must be transparent so the outer
   bubble background is the only visible background.
─────────────────────────────────────────────────────────────── */
#aiko-chatbot [data-testid="bot"] > div,
#aiko-chatbot [data-testid="bot"] > div > div,
#aiko-chatbot [data-testid="bot"] > div > div > div,
#aiko-chatbot [data-testid="bot"] .prose,
#aiko-chatbot [data-testid="bot"] .prose > *,
#aiko-chatbot [data-testid="bot"] .message,
#aiko-chatbot [data-testid="bot"] .message > div,
#aiko-chatbot [data-testid="user"] > div,
#aiko-chatbot [data-testid="user"] > div > div,
#aiko-chatbot [data-testid="user"] .prose,
#aiko-chatbot [data-testid="user"] .message,
#aiko-chatbot .bubble-wrap,
#aiko-chatbot .bubble-wrap > div,
#aiko-chatbot .wrap.svelte-byatnx,
#aiko-chatbot .wrap {
    background: transparent !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Text colour inside user bubble */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="user"] * {
    color: rgba(200,255,255,0.92) !important;
}

/* Text colour inside bot bubble — all regular weight, no italic */
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="bot"] * {
    color: rgba(230,215,255,0.92) !important;
    font-style: normal !important;
}

/* Last-resort: kill any inline background-color style Gradio injects */
#aiko-chatbot div[style*="background"],
#aiko-chatbot div[style*="background-color"] {
    background: transparent !important;
    background-color: transparent !important;
}

/* Search status line — styled but NOT italic */
#aiko-chatbot [data-testid="bot"] em {
    color: var(--ak-lav) !important;
    font-style: normal !important;
    font-size: 0.80rem !important;
    display: block !important;
    margin-bottom: 6px !important;
    opacity: 0.85 !important;
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

/* Hide avatars */
#aiko-chatbot .avatar-container { display: none !important; }

/* ── Input area ── */
.gradio-container .block:has(textarea[data-testid="textbox"]) {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 0 !important;
}

/* Visible frame around the entire input row */
.gradio-container .input-row,
.gradio-container div:has(> textarea[data-testid="textbox"]) {
    background: var(--ak-surface2) !important;
    border: 1px solid rgba(160,120,255,0.42) !important;
    border-radius: 28px !important;
    padding: 6px 8px 6px 18px !important;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;
}
.gradio-container .input-row:focus-within,
.gradio-container div:has(> textarea[data-testid="textbox"]):focus-within {
    border-color: rgba(180,142,255,0.70) !important;
    box-shadow: 0 0 0 3px rgba(160,120,255,0.10) !important;
}

/* The textarea itself stays transparent — frame is on the wrapper */
.gradio-container textarea[data-testid="textbox"] {
    background: transparent !important;
    border: none !important;
    outline: none !important;
    box-shadow: none !important;
    color: var(--ak-text) !important;
    caret-color: var(--ak-lav) !important;
    font-size: 0.875rem !important;
    line-height: 1.5 !important;
    resize: none !important;
    padding: 4px 0 !important;
    flex: 1 !important;
}
.gradio-container textarea[data-testid="textbox"]::placeholder {
    color: var(--ak-text-muted) !important;
}

/* Submit / stop buttons */
.gradio-container .textarea-wrapper button,
.gradio-container .input-row > button {
    background: rgba(160,120,255,0.16) !important;
    border: 1px solid rgba(160,120,255,0.32) !important;
    border-radius: 50% !important;
    color: rgba(200,170,255,0.9) !important;
    width: 34px !important; height: 34px !important; min-width: 34px !important;
    padding: 0 !important;
    display: flex !important; align-items: center !important; justify-content: center !important;
    flex-shrink: 0 !important;
    transition: background 0.2s !important;
}
.gradio-container .textarea-wrapper button:hover,
.gradio-container .input-row > button:hover {
    background: rgba(160,120,255,0.30) !important;
}

/* ── Sidebar ── */
#aiko-col { padding: 0 0 0 12px !important; }

/* ── Scrollbars ── */
* { scrollbar-width: thin; scrollbar-color: rgba(0,160,160,0.22) transparent; }
::-webkit-scrollbar       { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,160,160,0.22); border-radius: 2px; }

/* ── General text ── */
.gradio-container p,
.gradio-container label,
.gradio-container span { color: var(--ak-text) !important; }

.gradio-container .row { gap: 12px !important; }

#aiko-chatbot .placeholder { display: none !important; }
"""