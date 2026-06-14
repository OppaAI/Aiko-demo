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
#aiko-avatar-card {
  position: relative;
  border-radius: 22px;
  overflow: visible;
  border: 1px solid rgba(155,127,212,0.34);
  background: #080810;
  box-shadow: 0 22px 80px rgba(0,0,0,0.42);
}
#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: min(78vh, 760px);
  min-height: 480px;
  border: 0;
  background: #080810;
}
/* Audio: rendered but invisible so autoplay isn't blocked */
#aiko-audio {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
}
#aiko-audio * {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}
#aiko-tts-text { display: none !important; }
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
#aiko-emotion-label ~ #aiko-emotion-label,
body > #aiko-emotion-label,
.gradio-container > #aiko-emotion-label {
  display: none !important;
}
/* ── Hide Gradio message action buttons ── */
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
  bottom: 76px;
  width: 44%;
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
#aiko-chatbot.block,
#aiko-chatbot .block,
div:has(> #aiko-chatbot) {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}
/* Scrollable chatbot */
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
/* Caption-style text */
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
/* ── Input row ───────────────────────────────────────────────────── */
#aiko-input-row {
  position: absolute !important;
  left: 16px !important;
  right: 16px !important;
  bottom: 16px !important;
  z-index: 7 !important;
  display: flex !important;
  gap: 6px !important;
  align-items: center !important;
  flex-wrap: nowrap !important;
}
/* Flatten Gradio's wrapper divs so they don't break flex layout */
#aiko-input-row > div {
  display: contents !important;
}
#aiko-msg {
  flex: 1 1 auto;
  min-width: 0;
}
/* Remove Gradio textbox wrapper backgrounds */
#aiko-msg,
#aiko-msg > div,
#aiko-msg .wrap,
#aiko-msg .container {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  min-width: 0 !important;
  flex: 1 1 auto !important;
}
/* Actual textarea */
#aiko-msg textarea,
#aiko-msg input {
  background: rgba(8, 8, 16, 0.80) !important;
  background-color: rgba(8, 8, 16, 0.80) !important;
  backdrop-filter: blur(6px) !important;
  -webkit-backdrop-filter: blur(6px) !important;
  color: var(--aiko-accent) !important;
  border: 1px solid rgba(182,140,255,0.55) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  min-height: 42px !important;
  width: 100% !important;
}
textarea::placeholder, input::placeholder { color: var(--aiko-muted) !important; }
/* Mic + send buttons — fixed square size, never shrink */
#aiko-mic-btn,
#aiko-mic-btn button,
#aiko-send,
#aiko-send button {
  width: 42px !important;
  min-width: 42px !important;
  max-width: 42px !important;
  height: 42px !important;
  min-height: 42px !important;
  padding: 0 !important;
  border-radius: 10px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  flex-shrink: 0 !important;
  flex-grow: 0 !important;
}
/* Send button */
#aiko-send,
#aiko-send button {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
}
/* Mic button */
#aiko-mic-btn,
#aiko-mic-btn button {
  background: rgba(118, 82, 214, 0.25) !important;
  border: 1px solid rgba(182, 140, 255, 0.6) !important;
  box-shadow: none !important;
  font-size: 1.2rem !important;
  color: var(--aiko-accent) !important;
}
/* Hidden recorder — zero layout footprint */
#aiko-mic-audio {
  position: absolute !important;
  opacity: 0 !important;
  pointer-events: none !important;
  width: 0 !important;
  height: 0 !important;
  overflow: hidden !important;
}
#aiko-note { display: none; }
.gradio-container footer { display: none !important; }
.hide { display: none !important; }
"""
AIKO_CSS += r"""
/* ── Login modal overlay ──────────────────────────────────────────── */
#aiko-login-overlay {
  position: fixed !important;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(5, 5, 9, 0.78);
  backdrop-filter: blur(6px);
}
#aiko-login-overlay > div {
  position: static !important;
  inset: auto !important;
}
#aiko-login-card {
  width: min(380px, 90vw);
  max-height: 50vh;
  overflow-y: auto;
  padding: 20px 24px;
  border-radius: 18px;
  background: radial-gradient(circle at top, #1b1432 0, #080810 70%);
  border: 1px solid rgba(155,127,212,0.4);
  box-shadow: 0 22px 80px rgba(0,0,0,0.55);
  text-align: center;
}
#aiko-login-card h1 {
  color: #ecdeff;
  text-shadow: 0 0 18px rgba(155, 124, 255, .55);
  margin: 0 0 8px;
  font-size: 1.4rem;
  letter-spacing: .06em;
}
.aiko-subtitle {
  color: var(--aiko-muted);
  margin: 0 0 16px;
  font-size: 0.85rem;
}
.aiko-disclaimer {
  color: var(--aiko-muted);
  font-size: 0.85rem;
  line-height: 1.4;
  text-align: left;
  margin: 0 0 16px;
  padding: 10px 12px;
  border: 1px solid rgba(182,140,255,0.25);
  border-radius: 10px;
  background: rgba(118, 82, 214, 0.08);
}
#aiko-login-card button {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  border-radius: 10px !important;
  color: #fff !important;
  width: 100% !important;
  padding: 10px !important;
  font-weight: 600 !important;
}
"""