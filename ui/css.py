"""Shared CSS for the Gradio/Hugging Face Space interface."""
AIKO_CSS = r"""
:root {
  --aiko-bg: #080810;
  --aiko-panel: rgba(18, 14, 31, 0.86);
  --aiko-panel-solid: #100d1d;
  --aiko-border: rgba(155, 127, 212, 0.34);
  --aiko-text: #dacdff;
  --aiko-muted: #8c7ab6;
  --aiko-accent: #b68cff;
  --aiko-user: rgba(50, 34, 85, 0.88);
  --aiko-bot: rgba(25, 19, 41, 0.88);
}

html, body,
.gradio-container,
main, footer {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%) !important;
  color: var(--aiko-text) !important;
  margin: 0 !important;
  padding: 0 !important;
}

.gradio-container *, .gradio-container .prose, .gradio-container label {
  color: var(--aiko-text);
}

/* ── Top bar ─────────────────────────────────────────────── */
#aiko-topbar {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: rgba(8, 8, 16, 0.72);
  border-bottom: 1px solid var(--aiko-border);
  backdrop-filter: blur(8px);
  z-index: 10;
}
#aiko-topbar h1 {
  margin: 0;
  font-size: 1.05rem;
  letter-spacing: 0.18em;
  color: var(--aiko-accent) !important;
  text-transform: uppercase;
  font-weight: 600;
}

/* ── Main viewer container ───────────────────────────────── */
#aiko-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 12px 12px;
}

#aiko-viewer-wrap {
  position: relative;
  width: 100%;
  border: 1px solid var(--aiko-border);
  border-radius: 22px;
  overflow: hidden;
  background: #080810;
  box-shadow: 0 22px 80px rgba(0, 0, 0, 0.42);
}

/* ── VRM iframe — full viewer height ────────────────────── */
#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: min(72vh, 740px);
  min-height: 480px;
  border: 0;
  background: #080810;
}

/* ── Chat overlay — right 38% of the viewer ─────────────── */
#aiko-chat-overlay {
  position: absolute;
  top: 12px;
  right: 12px;
  bottom: 12px;
  width: 38%;
  display: flex;
  flex-direction: column;
  pointer-events: none; /* let clicks pass through to VRM by default */
  z-index: 5;
}

#aiko-chatbot {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  gap: 6px;
  padding: 8px 4px;
  /* custom scrollbar */
  scrollbar-width: thin;
  scrollbar-color: rgba(155,127,212,0.3) transparent;
  pointer-events: auto;
}

#aiko-chatbot::-webkit-scrollbar { width: 4px; }
#aiko-chatbot::-webkit-scrollbar-thumb { background: rgba(155,127,212,0.3); border-radius: 4px; }
#aiko-chatbot::-webkit-scrollbar-track { background: transparent; }

/* Override Gradio chatbot internals */
#aiko-chatbot,
#aiko-chatbot > div,
#aiko-chatbot .wrap,
#aiko-chatbot .bubble-wrap,
#aiko-chatbot .message-wrap {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  min-height: unset !important;
  height: 100% !important;
  max-height: 100% !important;
}

#aiko-chatbot .message,
#aiko-chatbot .bubble,
#aiko-chatbot [data-testid="bot"],
#aiko-chatbot [data-testid="user"] {
  border-radius: 14px !important;
  color: var(--aiko-text) !important;
  font-size: 0.82rem !important;
  line-height: 1.45 !important;
  padding: 8px 12px !important;
  max-width: 92% !important;
  backdrop-filter: blur(10px);
  border: 1px solid var(--aiko-border) !important;
  pointer-events: auto;
}

#aiko-chatbot .message.user,
#aiko-chatbot [data-testid="user"] {
  background: var(--aiko-user) !important;
  align-self: flex-end;
  margin-left: auto;
}

#aiko-chatbot .message.bot,
#aiko-chatbot [data-testid="bot"] {
  background: var(--aiko-bot) !important;
  align-self: flex-start;
}

/* ── Caption overlay — bottom of VRM ────────────────────── */
#aiko-caption-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  min-height: 52px;
  max-height: 110px;
  padding: 10px 22px 14px;
  background: linear-gradient(0deg, rgba(5,5,10,0.88) 0%, transparent 100%);
  display: flex;
  align-items: flex-end;
  pointer-events: none;
  z-index: 6;
}

#aiko-caption-text {
  color: #e8dcff;
  font-size: 0.88rem;
  line-height: 1.5;
  text-shadow: 0 1px 6px rgba(0,0,0,0.9), 0 0 18px rgba(100,60,180,0.5);
  letter-spacing: 0.01em;
  max-width: 58%;
  min-height: 1.4em;
  transition: opacity 0.3s;
}

#aiko-caption-text.empty { opacity: 0; }

/* ── Input row — below viewer ────────────────────────────── */
#aiko-input-section {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

#aiko-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

#aiko-input-row textarea,
#aiko-input-row input {
  background: rgba(10, 8, 18, 0.92) !important;
  color: var(--aiko-text) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  font-size: 0.9rem;
}

textarea::placeholder, input::placeholder {
  color: var(--aiko-muted) !important;
}

button.primary, button.variant-primary, #aiko-send {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
  border-radius: 12px !important;
}

/* ── Audio row — below input ─────────────────────────────── */
#aiko-audio-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

#aiko-audio,
#aiko-audio > div,
#aiko-audio .wrap {
  background: rgba(10, 8, 18, 0.72) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  flex: 1;
}

#aiko-audio audio {
  width: 100%;
  filter: hue-rotate(235deg) saturate(1.2);
}

#aiko-mic,
#aiko-mic > div {
  background: rgba(10, 8, 18, 0.72) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
}

/* Hide Gradio's own footer/label clutter */
.gradio-container footer { display: none !important; }
.hide { display: none !important; }
"""