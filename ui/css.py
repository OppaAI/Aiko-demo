"""Shared CSS for the Gradio livestream-style interface."""

AIKO_CSS = r"""
:root {
  --aiko-bg: #07060e;
  --aiko-stage: #090712;
  --aiko-panel: rgba(11, 8, 20, 0.78);
  --aiko-border: rgba(166, 128, 255, 0.34);
  --aiko-text: #d8cdfa;
  --aiko-muted: #8f7bbd;
  --aiko-accent: #c193ff;
  --aiko-cyan: #62f7ff;
  --aiko-user: rgba(31, 19, 54, 0.54);
  --aiko-bot: rgba(18, 14, 31, 0.34);
}

html, body, .gradio-container, .gradio-container > .main, main, footer {
  margin: 0 !important;
  padding: 0 !important;
  background: radial-gradient(circle at 50% -10%, #241a42 0, #150f2a 38%, #05050b 100%) !important;
  color: var(--aiko-text) !important;
  min-height: 100vh !important;
}

.gradio-container *, .gradio-container .prose, .gradio-container label {
  color: var(--aiko-text);
}

#aiko-shell {
  max-width: 1144px;
  margin: 0 auto;
  padding: 0 12px 18px;
  gap: 10px;
}

#aiko-topbar {
  height: 40px;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: rgba(8, 6, 18, 0.86);
  border-bottom: 1px solid var(--aiko-border);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.24);
}

#aiko-topbar h1 {
  margin: 0;
  font-size: 1rem;
  letter-spacing: 0.24em;
  color: var(--aiko-accent) !important;
  text-transform: uppercase;
  font-weight: 700;
}

#aiko-viewer-wrap {
  position: relative;
  width: 100%;
  height: min(710px, calc(100vh - 156px));
  min-height: 560px;
  flex: 0 0 auto !important;
  border: 1px solid var(--aiko-border);
  border-radius: 24px;
  overflow: hidden;
  background: var(--aiko-stage);
  box-shadow: 0 24px 90px rgba(0, 0, 0, 0.48), inset 0 0 0 1px rgba(255,255,255,0.02);
}

#aiko-vrm-frame {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
  background: #090712;
}

#aiko-chat-overlay {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  width: 42%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 72px 28px 96px 18px;
  pointer-events: none;
  z-index: 6;
  background: linear-gradient(270deg, rgba(5, 4, 12, 0.88) 0%, rgba(5, 4, 12, 0.62) 58%, transparent 100%);
}

#aiko-msg-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
  overflow: hidden;
  max-height: 78%;
  justify-content: center;
}

.aiko-live-line {
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  font-size: clamp(0.9rem, 1.55vw, 1.04rem);
  line-height: 1.35;
  text-shadow: 0 2px 8px rgba(0,0,0,0.92), 0 0 22px rgba(125,80,255,0.28);
  word-break: break-word;
  opacity: 0.96;
}

.aiko-live-name {
  font-weight: 800;
}

.aiko-msg-user {
  color: var(--aiko-cyan) !important;
  align-self: flex-end;
  text-align: right;
  max-width: 92%;
}

.aiko-msg-user .aiko-live-name { color: var(--aiko-cyan) !important; }

.aiko-msg-bot {
  color: var(--aiko-text) !important;
  align-self: flex-start;
  max-width: 86%;
}

.aiko-msg-bot .aiko-live-name { color: #cabaf2 !important; }

#aiko-now-speaking {
  position: absolute;
  left: 10%;
  right: 44%;
  bottom: 0;
  min-height: 68px;
  padding: 12px 18px 18px;
  display: flex;
  align-items: flex-end;
  pointer-events: none;
  z-index: 7;
  background: linear-gradient(0deg, rgba(5,5,10,.92) 0%, rgba(5,5,10,.52) 44%, transparent 100%);
}

#aiko-caption-text {
  color: #d9ceff !important;
  font-size: clamp(1.6rem, 3.1vw, 2.5rem);
  line-height: 1.08;
  font-weight: 800;
  letter-spacing: -0.035em;
  text-shadow: 0 2px 8px rgba(0,0,0,0.96), 0 0 24px rgba(157,115,255,0.4);
}

#aiko-caption-text:empty { display: none; }

#aiko-input-row, #aiko-input-row > div {
  background: transparent !important;
  border: none !important;
  align-items: center;
}

#aiko-input-row textarea, #aiko-input-row input {
  background: rgba(10, 8, 18, 0.92) !important;
  color: var(--aiko-text) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  font-size: 0.95rem;
  resize: none;
}

textarea::placeholder, input::placeholder { color: var(--aiko-muted) !important; }

button.primary, button.variant-primary, #aiko-send {
  background: linear-gradient(135deg, #7652d6, #bd7cff) !important;
  border: 0 !important;
  color: #fff !important;
  border-radius: 12px !important;
  height: 42px !important;
}

#aiko-mic, #aiko-mic > div, #aiko-mic .wrap, #aiko-audio, #aiko-audio > div, #aiko-audio .wrap {
  background: rgba(10, 8, 18, 0.72) !important;
  border: 1px solid var(--aiko-border) !important;
  border-radius: 14px !important;
  overflow: hidden;
}

#aiko-audio audio { width: 100%; filter: hue-rotate(235deg) saturate(1.2); }

#aiko-chat-state, #aiko-tts-text {
  position: absolute !important;
  left: -9999px !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  opacity: 0 !important;
  pointer-events: none !important;
}

.gradio-container footer { display: none !important; }

@media (max-width: 820px) {
  #aiko-viewer-wrap { min-height: 520px; height: calc(100vh - 170px); }
  #aiko-chat-overlay { width: 52%; padding-right: 14px; }
  #aiko-now-speaking { right: 50%; left: 4%; }
  .aiko-live-line { font-size: 0.82rem; }
}
"""