AIKO_CSS = r"""
:root {
  --aiko-bg: #080810;
  --aiko-text: #dacdff;
  --aiko-muted: #8c7ab6;
  --aiko-accent: #b68cff;
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

/* Avatar card becomes the relative anchor for overlays */
#aiko-avatar-card {
  position: relative;
  border-radius: 22px;
  overflow: hidden;
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

/* Audio + hidden tts text don't take layout space */
#aiko-audio { display: none !important; }
#aiko-tts-text { display: none !important; }

/* ── Borderless chat overlay, right side, no bubbles ───────── */
#aiko-chat-overlay {
  position: absolute;
  top: 16px;
  right: 16px;
  bottom: 90px;
  width: 42%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 8px;
  pointer-events: none;
  z-index: 5;
  overflow: hidden;
}
#aiko-chatbot {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  overflow-y: auto;
  scrollbar-width: none;
}
#aiko-chatbot::-webkit-scrollbar { display: none; }
#aiko-chatbot, #aiko-chatbot > div, #aiko-chatbot .wrap,
#aiko-chatbot .bubble-wrap, #aiko-chatbot .message-wrap {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  height: 100% !important;
  max-height: 100% !important;
}
/* No bubble chrome at all — plain text, like stream captions */
#aiko-chatbot .message,
#aiko-chatbot .bubble,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 4px 0 !important;
  font-size: 0.92rem !important;
  line-height: 1.5 !important;
  color: var(--aiko-text) !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.9), 0 0 16px rgba(100,60,180,0.45);
  max-width: 100% !important;
}
#aiko-chatbot [data-testid="user"] {
  color: #8be8ff !important;
  text-align: right;
}
#aiko-chatbot [data-testid="bot"] {
  color: var(--aiko-text) !important;
}

/* ── Input row floats over the bottom of the viewer ────────── */
#aiko-input-row {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 16px;
  display: flex;
  gap: 8px;
  align-items: center;
  z-index: 6;
}
#aiko-input-row textarea, #aiko-input-row input {
  background: rgba(10, 8, 18, 0.78) !important;
  color: var(--aiko-text) !important;
  border: 1px solid rgba(155,127,212,0.34) !important;
  border-radius: 14px !important;
  font-size: 0.9rem;
  backdrop-filter: blur(6px);
}
textarea::placeholder, input::placeholder { color: var(--aiko-muted) !important; }
button.primary, button.variant-primary, #aiko-send {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
  border-radius: 12px !important;
}

#aiko-mic, #aiko-mic > div {
  position: absolute;
  left: 16px;
  bottom: 64px;
  width: 200px;
  background: rgba(10, 8, 18, 0.78) !important;
  border: 1px solid rgba(155,127,212,0.34) !important;
  border-radius: 14px !important;
  backdrop-filter: blur(6px);
  z-index: 6;
}

#aiko-title { display: none; }
#aiko-note { display: none; }
.gradio-container footer { display: none !important; }
.hide { display: none !important; }
"""