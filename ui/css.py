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

/* ── Global page setup ─────────────────────────────────────────────── */
html, body {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%);
  color: var(--aiko-text);
  margin: 0;
  padding: 0;
  height: 100%;
}

.gradio-container {
  background: transparent !important;
  color: var(--aiko-text);
}

.gradio-container *, .gradio-container .prose, .gradio-container label {
  color: var(--aiko-text);
}

.gradio-container footer {
  display: none !important;
}

/* ── Hide Gradio loading/progress UI ───────────────────────────────── */
.toast-wrap,
.toast-body,
div[class*="toast"] {
  display: none !important;
}

/* ── Login overlay ─────────────────────────────────────────────────── */
#aiko-login-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: #0d0d1a;
  overflow-y: auto;
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

#aiko-login-overlay button {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  border-radius: 10px !important;
  color: #fff !important;
  padding: 12px 28px !important;
  font-size: 0.85rem !important;
  letter-spacing: .08em;
  box-shadow: 0 8px 30px rgba(155,124,255,0.35);
  cursor: pointer;
}

/* ── Shell ─────────────────────────────────────────────────────────── */
#aiko-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 12px 12px;
}

/* ── Title ─────────────────────────────────────────────────────────── */
#aiko-title-row {
  padding: 0;
}

#aiko-title {
  display: block;
  font-size: 1.4rem;
  font-weight: 600;
  letter-spacing: .08em;
  color: #ecdeff;
  text-shadow: 0 0 18px rgba(155, 124, 255, .55);
  padding: 10px 8px;
  text-align: left;
}

/* ── Avatar card ───────────────────────────────────────────────────── */
#aiko-avatar-card {
  position: relative;
  width: 100%;
  height: 80vh;
  overflow: hidden;
}

#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: 80vh;
  border: 0;
  background: #080810;
}

/* ── TTS textbox: hidden from layout ───────────────────────────────── */
#aiko-tts-text {
  display: none !important;
}

/* ── Audio: collapsed from layout ──────────────────────────────────── */
#aiko-audio {
  position: absolute;
  width: 0;
  height: 0;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
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
  z-index: 5;
  overflow: hidden;
  background: transparent;
}

#aiko-chatbot {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  overflow-y: auto !important;
  scrollbar-width: thin;
  scrollbar-color: rgba(182,140,255,0.35) transparent;
  max-height: 100%;
}

#aiko-chatbot::-webkit-scrollbar { width: 4px; }
#aiko-chatbot::-webkit-scrollbar-track { background: transparent; }
#aiko-chatbot::-webkit-scrollbar-thumb {
  background: rgba(182,140,255,0.35);
  border-radius: 4px;
}

#aiko-chatbot [data-testid="bubble-wrap"],
#aiko-chatbot .message,
#aiko-chatbot .message-row,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

#aiko-chatbot .message,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  font-size: 0.7rem !important;
  line-height: 1.3 !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.9), 0 0 16px rgba(100,60,180,0.45);
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

/* Hide chatbot action buttons (like/dislike/copy/edit) */
#aiko-chatbot [data-testid="like"],
#aiko-chatbot [data-testid="dislike"],
#aiko-chatbot [data-testid="copy"],
#aiko-chatbot [data-testid="edit"],
#aiko-chatbot .icon-button {
  display: none !important;
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
}

#aiko-msg {
  flex: 1 1 auto;
  min-width: 0;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

#aiko-msg textarea,
#aiko-msg input {
  background: transparent !important;
  color: var(--aiko-accent) !important;
  border: 1px solid rgba(182,140,255,0.55) !important;
  border-radius: 10px !important;
  box-shadow: none !important;
  min-height: 42px !important;
}

#aiko-msg textarea::placeholder,
#aiko-msg input::placeholder {
  color: var(--aiko-muted) !important;
}

#aiko-send,
#aiko-send button {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  border-radius: 8px !important;
  color: #fff !important;
  width: 42px !important;
  min-width: 42px !important;
  height: 42px !important;
  padding: 0 !important;
  flex-shrink: 0;
}

#aiko-mic-btn,
#aiko-mic-btn button {
  background: rgba(118, 82, 214, 0.25) !important;
  border: 1px solid rgba(182, 140, 255, 0.6) !important;
  border-radius: 8px !important;
  width: 42px !important;
  min-width: 42px !important;
  height: 42px !important;
  padding: 0 !important;
  flex-shrink: 0;
  font-size: 1.2rem !important;
  color: var(--aiko-accent) !important;
}

#aiko-mic-audio {
  display: none !important;
}
"""