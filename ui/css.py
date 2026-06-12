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
.gradio-container *, .gradio-container .prose, .gradio-container label {
  color: var(--aiko-text);
}

/* NEW BLOCK */
.gradio-container > .flex-1,
body > .gradio-container {
  height: 100vh !important;
  max-height: 100vh !important;
  overflow: hidden !important;
}
html, body {
  height: 100% !important;
  overflow: hidden !important;
}
.gradio-container {
  min-height: 100vh !important;
  transform: none !important;
}

#aiko-shell { max-width: 1180px; margin: 0 auto; padding: 0 12px 12px; }

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

/* Avatar card is the relative anchor for all overlays */
#aiko-avatar-card,
#aiko-avatar-card .html-container,
#aiko-avatar-card .prose {
  height: min(78vh, 760px) !important;
  max-height: min(78vh, 760px) !important;
  overflow: hidden !important;
}
#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: 100% !important;
  max-height: 100% !important;
  border: 0;
  background: #080810;
}


/* ── Audio: completely removed from layout flow ─────────────────────
   Gradio wraps gr.Audio in multiple divs; we must collapse ALL of them.
   The selector chain hits: the component block > the wrap > inner audio.
   Using !important on every dimension + overflow property to prevent
   any Gradio update from re-expanding it. */
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

/* ── Emotion label (top-left of avatar card) ──────────────────────── */
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

/* Hide any duplicate emotion-label nodes that Gradio's hydration may
   inject outside the avatar card (keep only the one inside #aiko-avatar-card) */
#aiko-emotion-label ~ #aiko-emotion-label,
body > #aiko-emotion-label,
.gradio-container > #aiko-emotion-label {
  display: none !important;
}

/* ── Hide Gradio message action buttons (copy/like/dislike/edit) ── */
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

/* ── Chat overlay: right side, borderless ─────────────────────────── */
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

/* Chatbot itself */
#aiko-chatbot,
#aiko-chatbot * {
  pointer-events: auto !important;
}

/* Kill every background/border Gradio injects on chatbot */
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

/* Kill outer Gradio block wrapper */
#aiko-chatbot.block,
#aiko-chatbot .block,
div:has(> #aiko-chatbot) {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* Scrollable chatbot with subtle scrollbar */
#aiko-chatbot {
  overflow-y: auto !important;
  scrollbar-width: thin;
  scrollbar-color: rgba(182,140,255,0.35) transparent;
  height: 100% !important;
  max-height: 100% !important;
  padding: 0 4px 0 0 !important;
}
#aiko-chatbot::-webkit-scrollbar {
  width: 4px;
}
#aiko-chatbot::-webkit-scrollbar-track {
  background: transparent;
}
#aiko-chatbot::-webkit-scrollbar-thumb {
  background: rgba(182,140,255,0.35);
  border-radius: 4px;
}

/* Caption-style text — small, tight, NO extra paragraph spacing */
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

/* Kill paragraph margins inside messages */
#aiko-chatbot p,
#aiko-chatbot .md p {
  margin: 0 0 2px 0 !important;
}

/* Message row spacing */
#aiko-chatbot .message-row,
#aiko-chatbot [class*="message-row"] {
  margin-bottom: 2px !important;
  padding: 0 !important;
}

/* User = light cyan right-aligned; bot = light lavender */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="user"] * {
  color: var(--aiko-user) !important;
  text-align: right;
}
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="bot"] * {
  color: var(--aiko-bot) !important;
}

/* ── Input row: pinned to bottom of avatar card ───────────────────── */
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

/* Make the textbox column shrink/grow */
#aiko-msg {
  flex: 1 1 auto;
  min-width: 0;
}

#aiko-mic-btn,
#aiko-mic-btn button,
#aiko-send,
#aiko-send button {
    width:48px !important;
    min-width:48px !important;
    height:48px !important;
    min-height:48px !important;
    padding:0 !important;
    border-radius:10px !important;
    display:flex !important;
    align-items:center !important;
    justify-content:center !important;
    flex-shrink:0;
}

/* Remove Gradio textbox wrapper */
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

/* Actual typing area */
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

/* Square send button */
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

/* ── Mic button ────────────────────────────────────────────────────── */
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

/* Hide the hidden recorder entirely from layout */
#aiko-mic-audio { display: none !important; }

#aiko-note { display: none; }
.gradio-container footer { display: none !important; }
.hide { display: none !important; }

/* ── Login overlay ─────────────────────────────────────────────────── */
/* ── Login overlay ─────────────────────────────────────────────────── */
/* ── Login overlay ─────────────────────────────────────────────────── */
#aiko-login-overlay {
  position: fixed !important;
  inset: 0 !important;
  width: 100vw !important;
  height: 100vh !important;
  flex: none !important;
  flex-grow: 0 !important;
  min-width: 0 !important;
  max-height: 100vh !important;
  contain: strict !important;
  z-index: 99999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 22px;
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%);
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
#aiko-login-overlay p {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: .12em;
  color: var(--aiko-muted);
  text-transform: uppercase;
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
}

#aiko-shell.locked {
  display: none !important;
}
"""