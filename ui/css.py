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

/* Avatar card is the relative anchor for all overlays */
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
  gap: 6px;
  pointer-events: none;  /* transparent gaps still pass clicks to VRM */
  z-index: 5;
  overflow: hidden;
}

/* Chatbot itself gets pointer events back so scroll works */
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

/* Hide chatbot scrollbar */
#aiko-chatbot {
  overflow-y: auto;
  scrollbar-width: none;
  height: 100% !important;
  max-height: 100% !important;
  padding: 0 !important;
}
#aiko-chatbot::-webkit-scrollbar { display: none; }

/* Caption-style text — small, tight */
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
  align-items: stretch;   /* all children same height */
  z-index: 6;
}

/* Transparent text input with lavender border */
#aiko-msg textarea,
#aiko-msg input,
#aiko-msg,
#aiko-msg > div,
#aiko-msg [class*="input"] {
  background: transparent !important;
  background-color: transparent !important;
  color: var(--aiko-accent) !important;
  border: 1px solid rgba(182, 140, 255, 0.6) !important;
  border-radius: 10px !important;
  font-size: 0.9rem !important;
  box-shadow: none !important;
  backdrop-filter: none !important;
  height: 100% !important;
  min-height: 42px;
}
textarea::placeholder, input::placeholder { color: var(--aiko-muted) !important; }

/* Square send button — matches row height */
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

/* ── Mic button: square, same size as send ────────────────────────── */
#aiko-mic-btn,
#aiko-mic-btn > div,
#aiko-mic-btn [class*="wrap"],
#aiko-mic-btn [class*="audio"] {
  background: rgba(118, 82, 214, 0.25) !important;
  border: 1px solid rgba(182, 140, 255, 0.6) !important;
  border-radius: 8px !important;
  box-shadow: none !important;
  width: 42px !important;
  min-width: 42px !important;
  height: 42px !important;
  min-height: 42px !important;
  padding: 0 !important;
  overflow: hidden;
  flex-shrink: 0;
}

/* Hide all the extra waveform/timer/label chrome Gradio adds to Audio */
#aiko-mic-btn .waveform-container,
#aiko-mic-btn .timestamps,
#aiko-mic-btn .controls,
#aiko-mic-btn .record-button-container > *:not(button),
#aiko-mic-btn [class*="waveform"],
#aiko-mic-btn [class*="timer"],
#aiko-mic-btn [class*="status"],
#aiko-mic-btn [class*="label"],
#aiko-mic-btn span {
  display: none !important;
}

/* Keep only the mic record button itself, centered */
#aiko-mic-btn button {
  background: transparent !important;
  border: none !important;
  color: var(--aiko-accent) !important;
  width: 42px !important;
  height: 42px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  font-size: 1.2rem !important;
}

#aiko-title { display: none; }
#aiko-note { display: none; }
.gradio-container footer { display: none !important; }
.hide { display: none !important; }
"""