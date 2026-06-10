"""Shared CSS for the Gradio/Hugging Face Space interface."""
AIKO_CSS = r"""
:root {
  --aiko-bg:           #080810;
  --aiko-panel:        rgba(18, 14, 31, 0.86);
  --aiko-panel-solid:  #100d1d;
  --aiko-border:       rgba(155, 127, 212, 0.34);
  --aiko-text:         #dacdff;
  --aiko-muted:        #8c7ab6;
  --aiko-accent:       #b68cff;
  --aiko-user:         rgba(50, 34, 85, 0.88);
  --aiko-bot:          rgba(25, 19, 41, 0.88);
}

/* ── Reset Gradio container bloat ──────────────────────────────────────────── */
html, body,
.gradio-container,
.gradio-container > .main,
.gradio-container > .main > .wrap,
main, footer {
  background: radial-gradient(circle at top, #1b1432 0, var(--aiko-bg) 44%, #050509 100%) !important;
  color: var(--aiko-text) !important;
  margin: 0 !important;
  padding: 0 !important;
  /* Never let Gradio itself stretch to fill viewport height */
  height: auto !important;
  min-height: 0 !important;
  overflow: visible !important;
}

/* Kill Gradio's flex-grow that causes infinite downward stretch */
.gradio-container .contain,
.gradio-container .gap,
.gradio-container .flex,
.gradio-container > div {
  flex: 0 0 auto !important;
  height: auto !important;
}

.gradio-container *, .gradio-container .prose, .gradio-container label {
  color: var(--aiko-text);
}

/* ── Top bar ─────────────────────────────────────────────────────────────── */
#aiko-topbar {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  background: rgba(8, 8, 16, 0.72);
  border-bottom: 1px solid var(--aiko-border);
  backdrop-filter: blur(8px);
}
#aiko-topbar h1 {
  margin: 0;
  font-size: 1.05rem;
  letter-spacing: 0.18em;
  color: var(--aiko-accent) !important;
  text-transform: uppercase;
  font-weight: 600;
}

/* ── Shell column ─────────────────────────────────────────────────────────── */
#aiko-shell {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 12px 16px;
  display: flex !important;
  flex-direction: column !important;
  gap: 8px;
  height: auto !important;
}

/* ── Viewer wrapper — FIXED height, position:relative for overlays ──────── */
#aiko-viewer-wrap {
  position: relative;          /* overlay anchors */
  width: 100%;
  height: 520px;               /* fixed — never grows */
  flex: 0 0 520px !important;  /* prevent flex-stretch */
  border: 1px solid var(--aiko-border);
  border-radius: 22px;
  overflow: hidden;
  background: #080810;
  box-shadow: 0 22px 80px rgba(0,0,0,0.42);
}

/* ── VRM iframe fills the wrapper exactly ─────────────────────────────────── */
#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: 100%;               /* fills the fixed-height wrapper */
  border: 0;
  background: #080810;
}

/* ── Chat message overlay — right 40%, absolute inside wrapper ───────────── */
#aiko-chat-overlay {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 40%;
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 12px 10px 12px 4px;
  pointer-events: none;
  z-index: 5;
  /* subtle right-side gradient so text is readable over the 3D scene */
  background: linear-gradient(270deg, rgba(5,4,12,0.55) 0%, transparent 100%);
}

#aiko-msg-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow-y: auto;
  max-height: 100%;
  scrollbar-width: thin;
  scrollbar-color: rgba(155,127,212,0.25) transparent;
  pointer-events: auto;
  padding-right: 4px;
}
#aiko-msg-list::-webkit-scrollbar { width: 3px; }
#aiko-msg-list::-webkit-scrollbar-thumb { background: rgba(155,127,212,0.25); border-radius: 3px; }

.aiko-msg {
  border-radius: 13px;
  font-size: 0.80rem;
  line-height: 1.45;
  padding: 7px 11px;
  max-width: 94%;
  backdrop-filter: blur(10px);
  border: 1px solid var(--aiko-border);
  word-break: break-word;
}
.aiko-msg-user {
  background: var(--aiko-user);
  align-self: flex-end;
  text-align: right;
}
.aiko-msg-bot {
  background: var(--aiko-bot);
  align-self: flex-start;
}

/* ── Input row — below viewer, fixed height ──────────────────────────────── */
#aiko-input-row,
#aiko-input-row > div {
  background: transparent !important;
  border: none !important;
  flex: 0 0 auto !important;
  height: auto !important;
  align-items: center;
}

#aiko-input-row textarea,
#aiko-input-row input {
  background: rgba(10, 8, 18, 0.92) !important;
  color: var(--aiko-text) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  font-size: 0.9rem;
  resize: none;
}

textarea::placeholder, input::placeholder {
  color: var(--aiko-muted) !important;
}

button.primary, button.variant-primary, #aiko-send {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
  border-radius: 12px !important;
  height: 42px !important;
  flex: 0 0 auto !important;
}

/* ── Mic button ──────────────────────────────────────────────────────────── */
#aiko-mic,
#aiko-mic > div,
#aiko-mic .wrap {
  background: rgba(10, 8, 18, 0.72) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  height: 42px !important;
  flex: 0 0 auto !important;
  overflow: hidden;
}

/* ── Audio waveform player ───────────────────────────────────────────────── */
#aiko-audio,
#aiko-audio > div,
#aiko-audio .wrap {
  background: rgba(10, 8, 18, 0.72) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  flex: 0 0 auto !important;
  height: auto !important;
}
#aiko-audio audio {
  width: 100%;
  filter: hue-rotate(235deg) saturate(1.2);
}

/* ── Fully hide the real chatbot (state only, no display) ────────────────── */
#aiko-chatbot-hidden,
[id="aiko-chatbot-hidden"] {
  display: none !important;
  visibility: hidden !important;
  height: 0 !important;
  overflow: hidden !important;
}

/* ── Kill Gradio footer ──────────────────────────────────────────────────── */
.gradio-container footer { display: none !important; }
"""