"""Shared CSS for the Gradio/Hugging Face Space interface."""
AIKO_CSS = r"""
:root {
  --aiko-bg: #080810;
  --aiko-text: #dacdff;
  --aiko-muted: #8c7ab6;
  --aiko-accent: #b68cff;
  --aiko-user: #9be8ff;
  --aiko-bot: #d8c8ff;
}
html, body, .gradio-container, main, footer {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%) !important;
  color: var(--aiko-text) !important;
  margin: 0 !important;
  padding: 0 !important;
}
/* Lock everything to viewport — no min-height, no growth */
html,
body,
.gradio-container,
.gradio-container > .flex-1,
body > .gradio-container,
main {
  height: 100vh !important;
  max-height: 100vh !important;
  min-height: unset !important;
  overflow: hidden !important;
  transform: none !important;
}
/* Kill Gradio inner flex growth */
.gradio-container .flex-col,
.gradio-container > div,
.gradio-container .overflow-y-auto {
  min-height: unset !important;
  overflow: hidden !important;
}
.gradio-container *, .gradio-container .prose, .gradio-container label {
  color: var(--aiko-text);
}
/* ── Hide Gradio loading/progress bar ──────────────────────────────── */
#cosmos-spinner,
.progress-bar,
.loader,
[class*="progress"],
[class*="loading-bar"],
[id*="cosmos"],
.toast-wrap,
.toast-body,
.svelte-toast,
div[class*="toast"],
div[class*="status"] {
  display: none !important;
  opacity: 0 !important;
  visibility: hidden !important;
}
/* ── Shell ─────────────────────────────────────────────────────────── */
#aiko-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 12px 12px;
  height: 100vh;
  max-height: 100vh;
  overflow: hidden;
}
#aiko-shell.locked {
  display: none !important;
}
/* ── Shell unlocked state ───────────────────────────────────────────── */
#aiko-shell:not(.locked),
#aiko-shell:not(.locked) > div,
#aiko-shell:not(.locked) > .block,
#aiko-shell:not(.locked) > div > div {
  height: 100vh !important;
  max-height: 100vh !important;
  min-height: unset !important;
  overflow: hidden !important;
}
/* ── Main row containment ───────────────────────────────────────────── */
#aiko-shell > .block > div,
#aiko-shell .gap,
#aiko-shell > div > div {
  height: calc(100vh - 70px) !important;
  max-height: calc(100vh - 70px) !important;
  min-height: unset !important;
  overflow: hidden !important;
  flex-shrink: 0;
}
/* ── Title header ──────────────────────────────────────────────────── */
#aiko-title {
  display: block;
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: .08em;
  color: #ecdeff;
  text-shadow: 0 0 18px rgba(155, 124, 255, .55);
  padding: 10px 8px 10px;
  text-align: left;
}
/* ── Avatar card ───────────────────────────────────────────────────── */
#aiko-avatar-card,
#aiko-avatar-card .html-container,
#aiko-avatar-card .prose {
  height: calc(100vh - 70px) !important;
  max-height: calc(100vh - 70px) !important;
  min-height: unset !important;
  overflow: hidden !important;
}
/* Avatar card Gradio column wrapper */
#aiko-avatar-card > .wrap,
#aiko-avatar-card > div,
div:has(> #aiko-avatar-card) {
  height: calc(100vh - 70px) !important;
  max-height: calc(100vh - 70px) !important;
  min-height: unset !important;
  overflow: hidden !important;
}
#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: calc(100vh - 70px) !important;
  max-height: calc(100vh - 70px) !important;
  min-height: unset !important;
  border: 0;
  background: #080810;
}
/* ── TTS textbox: hidden from layout entirely ──────────────────────── */
#aiko-tts-text,
#aiko-tts-text.block,
div:has(> #aiko-tts-text),
div:has(> div > #aiko-tts-text) {
  display: none !important;
  height: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}
/* ── Audio: collapsed from layout flow ─────────────────────────────── */
#aiko-audio,
#aiko-audio > *,
div:has(> #aiko-audio),
div:has(> div > #aiko-audio) {
  position: absolute !important;
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  height: 0 !important;
  min-height: 0 !important;
  max-height: 0 !important;
  padding: 0 !important;
  margin: 0 !important;
  border: none !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
  visibility: hidden !important;
}
/* ── Emotion label ─────────────────────────────────────────────────── */
#aiko-emotion-label {
  position: absolute;
  top: 10px;
  left: 14px;
  z-index: 10;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: rgba(220, 200, 255, 0.75);
  text-shadow: 0 0 8px rgba(150,100,255,0.6);
  pointer-events: none;
  transition: opacity 0.4s ease;
}
#aiko-emotion-label ~ #aiko-emotion-label,
body > #aiko-emotion-label,
.gradio-container > #aiko-emotion-label {
  display: none !important;
}
/* ── Hide Gradio chatbot action buttons ────────────────────────────── */
#aiko-chatbot .message-buttons,
#aiko-chatbot .icon-button,
#aiko-chatbot [data-testid="like"],
#aiko-chatbot [data-testid="dislike"],
#aiko-chatbot [data-testid="copy"],
#aiko-chatbot [data-testid="edit"],
#aiko-chatbot button.copy,
#aiko-chatbot button.edit,
#aiko-chatbot .action-button,
#aiko-chatbot [class*="action"],
#aiko-chatbot [class*="button-row"],
#aiko-chatbot [class*="buttons"] {
  display: none !important;
}
/* ── Chat overlay ──────────────────────────────────────────────────── */
#aiko-chat-overlay {
  position: absolute;
  top: 16px;
  right: 16px;
  bottom: 90px;
  width: 42%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 0;
  pointer-events: auto;
  z-index: 5;
  overflow: hidden;
}
#aiko-chatbot,
#aiko-chatbot * {
  pointer-events: auto !important;
}
/* Kill Gradio backgrounds/borders on chatbot */
#aiko-chatbot,
#aiko-chatbot > div,
#aiko-chatbot > div > div,
#aiko-chatbot .wrap,
#aiko-chatbot .bubble-wrap,
#aiko-chatbot .message-wrap,
#aiko-chatbot .message-wrap > div,
#aiko-chatbot .message-row,
#aiko-chatbot .message-row > div,
#aiko-chatbot .message-row .prose,
#aiko-chatbot .chat-message,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="bot"] *,
#aiko-chatbot [data-testid="user"] *,
#aiko-chatbot .md,
#aiko-chatbot .md > *,
#aiko-chatbot [class*="message"],
#aiko-chatbot [class*="bubble"],
#aiko-chatbot [class*="wrap"],
#aiko-chatbot [class*="chat"] {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
#aiko-chatbot.block,
#aiko-chatbot .block,
div:has(> #aiko-chatbot) {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
#aiko-chatbot {
  overflow-y: auto !important;
  scrollbar-width: thin;
  scrollbar-color: rgba(182,140,255,0.35) transparent;
  height: 100% !important;
  max-height: 100% !important;
  padding: 0 4px 0 0 !important;
}
#aiko-chatbot::-webkit-scrollbar { width: 4px; }
#aiko-chatbot::-webkit-scrollbar-track { background: transparent; }
#aiko-chatbot::-webkit-scrollbar-thumb {
  background: rgba(182,140,255,0.35);
  border-radius: 4px;
}
#aiko-chatbot .message,
#aiko-chatbot .bubble,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  padding: 1px 0 !important;
  margin: 0 !important;
  font-size: 0.66rem !important;
  line-height: 1.25 !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.9), 0 0 16px rgba(100,60,180,0.45);
  max-width: 100% !important;
}
#aiko-chatbot p,
#aiko-chatbot .md p {
  margin: 0 0 2px 0 !important;
}
#aiko-chatbot .message-row,
#aiko-chatbot [class*="message-row"] {
  margin-bottom: 2px !important;
  padding: 0 !important;
}
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="user"] * {
  color: var(--aiko-user) !important;
  text-align: right;
}
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="bot"] * {
  color: var(--aiko-bot) !important;
}
/* ── Input row ─────────────────────────────────────────────────────── */
#aiko-input-row {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 16px;
  display: flex;
  gap: 6px;
  align-items: stretch;
  z-index: 6;
  flex-wrap: nowrap;
}
#aiko-msg {
  flex: 1 1 auto;
  min-width: 0;
}
#aiko-msg,
#aiko-msg > div,
#aiko-msg .wrap,
#aiko-msg .container {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
#aiko-msg textarea,
#aiko-msg input {
  background: transparent !important;
  background-color: transparent !important;
  color: var(--aiko-accent) !important;
  border: 1px solid rgba(182,140,255,0.55) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  min-height: 42px !important;
}
textarea::placeholder, input::placeholder { color: var(--aiko-muted) !important; }
#aiko-send,
#aiko-send button {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  border-radius: 8px !important;
  color: #fff !important;
  width: 42px !important;
  min-width: 42px !important;
  height: 42px !important;
  min-height: 42px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  flex-shrink: 0;
}
#aiko-mic-btn,
#aiko-mic-btn button {
  background: rgba(118, 82, 214, 0.25) !important;
  border: 1px solid rgba(182, 140, 255, 0.6) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  width: 42px !important;
  min-width: 42px !important;
  height: 42px !important;
  min-height: 42px !important;
  padding: 0 !important;
  flex-shrink: 0;
  font-size: 1.2rem !important;
  color: var(--aiko-accent) !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}
#aiko-mic-audio { display: none !important; }
#aiko-note { display: none; }
.gradio-container footer { display: none !important; }
.hide { display: none !important; }
/* ── Login overlay ─────────────────────────────────────────────────── */
#aiko-login-overlay {
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 9999 !important;
  display: flex !important;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #0d0d1a;
  overflow-y: auto !important;
  overflow-x: hidden !important;
}
#aiko-login-overlay.hidden {
  display: none !important;
}
#aiko-login-overlay h1 {
  margin: 0;
  font-size: 1.6rem;
  font-weight: 600;
  letter-spacing: .28em;
  text-transform: uppercase;
  color: #ecdeff;
  text-shadow: 0 0 18px rgba(155, 124, 255, .55);
}
#aiko-login-overlay .aiko-subtitle {
  margin: 0;
  font-size: 1.0rem;
  letter-spacing: .12em;
  color: var(--aiko-muted);
  text-transform: uppercase;
  font-weight: 600;
}
#aiko-login-overlay .aiko-disclaimer {
  margin: 0 auto;
  max-width: 540px;
  font-size: 0.95rem;
  line-height: 1.6;
  color: var(--aiko-accent);
  opacity: 0.85;
  text-align: left;
  font-style: italic;
  padding: 14px 24px 0;
  border-top: 1px solid rgba(182, 140, 255, 0.12);
}
/* Constrain the LoginButton and all its Gradio wrappers */
/* Constrain ONLY the login button wrapper */
#aiko-login-overlay .block:has(button),
#aiko-login-overlay .wrap:has(button) {
  width: auto !important;
  min-width: unset !important;
  max-width: 280px !important;
  flex-shrink: 0;
  min-height: unset !important;
  height: auto !important;
  overflow: visible !important;
}

/* Let all other wrappers be full width */
#aiko-login-overlay > div,
#aiko-login-overlay > div > div,
#aiko-login-overlay .block,
#aiko-login-overlay .wrap {
  width: auto !important;
  min-width: unset !important;
  max-width: 100% !important;
  flex-shrink: 0;
  min-height: unset !important;
  height: auto !important;
  overflow: visible !important;
}
#aiko-login-overlay button {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  border-radius: 10px !important;
  color: #fff !important;
  padding: 12px 28px !important;
  font-size: 0.85rem !important;
  letter-spacing: .08em;
  box-shadow: 0 8px 30px rgba(155,124,255,0.35);
  width: auto !important;
  min-width: unset !important;
  cursor: pointer;
}
"""