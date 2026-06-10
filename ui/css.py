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

/* Audio kept rendered (not display:none) so autoplay isn't blocked,
   but visually invisible */
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
  gap: 6px;
  pointer-events: none;
  z-index: 5;
  overflow: hidden;
}

/* Kill every background/border layer Gradio injects on the chatbot */
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

/* Kill the outer Gradio block wrapper that wraps #aiko-chatbot */
#aiko-chatbot.block,
#aiko-chatbot .block,
div:has(> #aiko-chatbot) {
  background: transparent !important;
  background-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* Hide chatbot scrollbar — the iframe owns its own scroll */
#aiko-chatbot {
  overflow-y: auto;
  scrollbar-width: none;
  height: 100% !important;
  max-height: 100% !important;
  padding: 0 !important;
}
#aiko-chatbot::-webkit-scrollbar { display: none; }

/* Plain caption-style text — smaller font, tighter line height */
#aiko-chatbot .message,
#aiko-chatbot .bubble,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  padding: 2px 0 !important;
  font-size: 0.80rem !important;
  line-height: 1.3 !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.9), 0 0 16px rgba(100,60,180,0.45);
  max-width: 100% !important;
}

/* Colors: user = light cyan, assistant = light lavender */
#aiko-chatbot [data-testid="user"],
#aiko-chatbot [data-testid="user"] * {
  color: var(--aiko-user) !important;
  text-align: right;
}
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="bot"] * {
  color: var(--aiko-bot) !important;
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

/* Transparent input box with lavender border and lavender text */
#aiko-input-row textarea,
#aiko-input-row input,
#aiko-input-row .input-wrap,
#aiko-input-row [class*="input"] {
  background: transparent !important;
  background-color: transparent !important;
  color: var(--aiko-accent) !important;
  border: 1px solid rgba(182, 140, 255, 0.6) !important;
  border-radius: 14px !important;
  font-size: 0.9rem;
  backdrop-filter: none !important;
  box-shadow: none !important;
}

textarea::placeholder, input::placeholder {
  color: var(--aiko-muted) !important;
}

/* Square send button */
button.primary, button.variant-primary, #aiko-send {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
  border-radius: 4px !important;
  aspect-ratio: 1 / 1;
  min-width: 42px;
  min-height: 42px;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
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